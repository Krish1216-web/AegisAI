import uuid
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from app.models.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphNode, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.entity_extraction.models import ExtractedRelationship
from app.schemas.knowledge_graph import EdgeCreate

class RelationshipValidationResult(BaseModel):
    is_valid: bool
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_detected: bool = False
    conflict_type: Optional[str] = None

class RelationshipExtractor:
    """
    Production-grade Relationship Extraction and persistence service.
    Validates, scores, deduplicates, and commits semantic edges between resolved
    Knowledge Graph nodes with full provenance and tenant boundary enforcement.
    """
    def __init__(self, db: Session):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)

    def validate_relationship(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        source_node: Optional[KnowledgeGraphNode],
        target_node: Optional[KnowledgeGraphNode],
        rel: ExtractedRelationship
    ) -> RelationshipValidationResult:
        """
        Validates entity relationships against graph structural and tenant isolation rules.
        """
        if not source_node or not target_node:
            return RelationshipValidationResult(
                is_valid=False,
                reason="Source or target entity node does not exist in graph.",
                confidence=0.0
            )

        if source_node.id == target_node.id:
            return RelationshipValidationResult(
                is_valid=False,
                reason="Self-referencing relationship loops are not permitted.",
                confidence=0.0
            )

        # Cross-tenant boundary verification
        if source_node.workspace_id != workspace_id or target_node.workspace_id != workspace_id:
            return RelationshipValidationResult(
                is_valid=False,
                reason="Cross-workspace entity connection violation.",
                confidence=0.0
            )

        if source_node.user_id != user_id or target_node.user_id != user_id:
            return RelationshipValidationResult(
                is_valid=False,
                reason="Cross-user entity connection violation.",
                confidence=0.0
            )

        # Validate relationship enum type
        valid_rel_types = {rt.value for rt in RelationshipType}
        if rel.relationship_type not in valid_rel_types:
            return RelationshipValidationResult(
                is_valid=False,
                reason=f"Invalid relationship type '{rel.relationship_type}'. Allowed types: {sorted(list(valid_rel_types))}",
                confidence=0.0
            )

        # Contradiction check against existing inverse or opposing edges
        conflict_detected = False
        conflict_type = None
        opposing_edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.source_node_id == target_node.id,
            KnowledgeGraphEdge.target_node_id == source_node.id
        ).all()

        # Check for contradictory asymmetric relationship pairings
        for opp in opposing_edges:
            if rel.relationship_type in (RelationshipType.CONTAINS.value, RelationshipType.PART_OF.value) and opp.relationship_type == rel.relationship_type:
                conflict_detected = True
                conflict_type = f"Cyclic hierarchy contradiction: {source_node.name} and {target_node.name} mutually assert {rel.relationship_type}."

        bounded_confidence = max(0.1, min(1.0, rel.confidence))

        return RelationshipValidationResult(
            is_valid=True,
            reason="Relationship passed structural and tenancy validation.",
            confidence=bounded_confidence,
            conflict_detected=conflict_detected,
            conflict_type=conflict_type
        )

    def persist_relationship(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_node: KnowledgeGraphNode,
        target_node: KnowledgeGraphNode,
        rel: ExtractedRelationship
    ) -> Optional[KnowledgeGraphEdge]:
        """
        Creates or idempotently updates a knowledge graph edge between two resolved nodes.
        Attaches rich provenance and conflict indicators to edge properties.
        """
        validation = self.validate_relationship(
            workspace_id=workspace_id,
            user_id=user_id,
            source_node=source_node,
            target_node=target_node,
            rel=rel
        )

        if not validation.is_valid:
            logger.warning(f"Relationship validation rejected: {validation.reason}")
            return None

        # Check for existing duplicate edge
        existing_edge = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            KnowledgeGraphEdge.source_node_id == source_node.id,
            KnowledgeGraphEdge.target_node_id == target_node.id,
            KnowledgeGraphEdge.relationship_type == rel.relationship_type
        ).first()

        # Build clean properties dictionary with provenance
        props: Dict[str, Any] = {
            "source_text": rel.source_text[:500] if rel.source_text else "",
            "document_id": str(rel.document_id) if rel.document_id else None,
            "chunk_id": str(rel.chunk_id) if rel.chunk_id else None,
            "page_number": getattr(rel, "page_number", None),
            "extraction_method": "entity_extractor",
            "conflict_indicators": [validation.conflict_type] if validation.conflict_detected else []
        }

        if existing_edge:
            # Update confidence if higher
            updated = False
            if validation.confidence > existing_edge.confidence:
                existing_edge.confidence = validation.confidence
                updated = True

            # Merge properties / meta_data
            current_props = dict(existing_edge.meta_data or {})
            if props.get("document_id") and not current_props.get("document_id"):
                current_props["document_id"] = props["document_id"]
                updated = True
            if validation.conflict_detected:
                conflicts = current_props.get("conflict_indicators", [])
                if validation.conflict_type not in conflicts:
                    conflicts.append(validation.conflict_type)
                    current_props["conflict_indicators"] = conflicts
                    updated = True

            if updated:
                existing_edge.meta_data = current_props
                self.db.commit()
                self.db.refresh(existing_edge)
            return existing_edge

        # Create new edge
        edge_data = EdgeCreate(
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            relationship_type=rel.relationship_type,
            confidence=validation.confidence,
            properties=props
        )

        try:
            return self.kg_service.create_edge(
                user_id=user_id,
                workspace_id=workspace_id,
                edge_data=edge_data
            )
        except Exception as e:
            logger.warning(f"Could not persist relationship edge: {e}")
            return None
