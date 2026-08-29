import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.models.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphNode, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.entity_extraction.models import ExtractedRelationship
from app.schemas.knowledge_graph import EdgeCreate

class RelationshipExtractor:
    """
    Constructs and persists validated relationship edges between resolved knowledge graph nodes.
    Ensures idempotent edge insertion and workspace isolation.
    """
    def __init__(self, db: Session):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)

    def persist_relationship(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_node: KnowledgeGraphNode,
        target_node: KnowledgeGraphNode,
        rel: ExtractedRelationship
    ) -> Optional[KnowledgeGraphEdge]:
        """
        Creates or updates a knowledge graph edge between two resolved nodes.
        """
        if source_node.id == target_node.id:
            return None

        # Verify tenant ownership
        if source_node.workspace_id != workspace_id or target_node.workspace_id != workspace_id:
            logger.warning("Attempted to connect nodes across workspace boundaries.")
            return None

        # Check for existing edge
        existing_edge = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            KnowledgeGraphEdge.source_node_id == source_node.id,
            KnowledgeGraphEdge.target_node_id == target_node.id,
            KnowledgeGraphEdge.relationship_type == rel.relationship_type
        ).first()

        if existing_edge:
            # Update confidence if higher
            if rel.confidence > existing_edge.confidence:
                existing_edge.confidence = rel.confidence
                self.db.commit()
                self.db.refresh(existing_edge)
            return existing_edge

        # Create new edge
        edge_data = EdgeCreate(
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            relationship_type=rel.relationship_type,
            confidence=rel.confidence,
            properties={
                "source_text": rel.source_text,
                "document_id": str(rel.document_id) if rel.document_id else None,
                "chunk_id": str(rel.chunk_id) if rel.chunk_id else None
            } if (rel.source_text or rel.document_id) else None
        )

        try:
            return self.kg_service.create_edge(
                user_id=user_id,
                workspace_id=workspace_id,
                edge_data=edge_data
            )
        except Exception as e:
            logger.warning(f"Could not persist edge: {e}")
            return None
