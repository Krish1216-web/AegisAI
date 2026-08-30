import uuid
import difflib
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.entity_extraction.models import ExtractedEntity
from app.services.entity_extraction.normalizer import EntityNormalizer, KNOWN_ALIASES
from app.schemas.knowledge_graph import NodeCreate

class ResolutionResult(BaseModel):
    matched: bool
    strategy: str # "exact" | "alias" | "normalized_key" | "type_aware" | "fuzzy" | "created_new"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    node_id: Optional[uuid.UUID] = None
    canonical_name: str
    entity_type: str
    reason: str

    class Config:
        arbitrary_types_allowed = True

class EntityResolver:
    """
    Production-grade Entity Resolution engine.
    Resolves entity mentions across documents, chunks, and user prompts to canonical
    Knowledge Graph nodes using deterministic multi-strategy matching, type awareness,
    fuzzy comparison, and strict workspace isolation.
    """
    def __init__(self, db: Session):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)

    def resolve_entity(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        extracted: ExtractedEntity,
        allow_fuzzy: bool = True,
        fuzzy_threshold: float = 0.88
    ) -> Tuple[Optional[KnowledgeGraphNode], ResolutionResult]:
        """
        Executes ordered resolution strategies:
        1. Exact Canonical Match (case-insensitive & stripped)
        2. Alias Dictionary Match
        3. Normalized Key Match
        4. Type-Aware Validation
        5. Controlled Fuzzy Similarity Match
        """
        raw_name = extracted.name or ""
        canonical_name, lookup_key, resolved_type = EntityNormalizer.canonicalize(
            raw_name, fallback_type=extracted.entity_type
        )

        if not canonical_name or not lookup_key:
            return None, ResolutionResult(
                matched=False,
                strategy="invalid_input",
                confidence=0.0,
                canonical_name=raw_name,
                entity_type=extracted.entity_type,
                reason="Empty or unresolvable entity name."
            )

        # 1. Exact canonical match in workspace
        exact_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id,
            func.lower(KnowledgeGraphNode.name) == canonical_name.lower(),
            KnowledgeGraphNode.node_type == resolved_type
        ).first()

        if exact_node:
            lowered_raw = raw_name.lower().strip()
            is_alias = lowered_raw in KNOWN_ALIASES and lowered_raw != canonical_name.lower()
            return exact_node, ResolutionResult(
                matched=True,
                strategy="alias" if is_alias else "exact",
                confidence=0.98 if is_alias else 1.0,
                node_id=exact_node.id,
                canonical_name=exact_node.name,
                entity_type=exact_node.node_type,
                reason=f"Alias match: '{raw_name}' -> '{exact_node.name}'." if is_alias else f"Exact match on canonical name '{exact_node.name}' and type '{resolved_type}'."
            )

        # 2. Alias match
        lowered_raw = raw_name.lower().strip()
        if lowered_raw in KNOWN_ALIASES:
            alias_canonical, alias_type = KNOWN_ALIASES[lowered_raw]
            alias_node = self.db.query(KnowledgeGraphNode).filter(
                KnowledgeGraphNode.workspace_id == workspace_id,
                KnowledgeGraphNode.user_id == user_id,
                func.lower(KnowledgeGraphNode.name) == alias_canonical.lower(),
                KnowledgeGraphNode.node_type == alias_type
            ).first()

            if alias_node:
                return alias_node, ResolutionResult(
                    matched=True,
                    strategy="alias",
                    confidence=0.98,
                    node_id=alias_node.id,
                    canonical_name=alias_node.name,
                    entity_type=alias_node.node_type,
                    reason=f"Alias match: '{raw_name}' -> '{alias_node.name}'."
                )

        # 3. Normalized Key Match
        # Fetch candidate nodes for the workspace with matching entity type
        workspace_nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id,
            KnowledgeGraphNode.node_type == resolved_type
        ).all()

        for node in workspace_nodes:
            node_key = EntityNormalizer.get_lookup_key(node.name)
            if node_key == lookup_key:
                return node, ResolutionResult(
                    matched=True,
                    strategy="normalized_key",
                    confidence=0.95,
                    node_id=node.id,
                    canonical_name=node.name,
                    entity_type=node.node_type,
                    reason=f"Normalized key match: key '{lookup_key}' matches existing node '{node.name}'."
                )

        # 4. Controlled Fuzzy Similarity Match (Type-Aware)
        if allow_fuzzy and len(canonical_name) >= 4:
            best_node: Optional[KnowledgeGraphNode] = None
            best_ratio: float = 0.0

            for node in workspace_nodes:
                ratio = difflib.SequenceMatcher(
                    None,
                    canonical_name.lower(),
                    node.name.lower()
                ).ratio()

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_node = node

            if best_node and best_ratio >= fuzzy_threshold:
                return best_node, ResolutionResult(
                    matched=True,
                    strategy="fuzzy",
                    confidence=round(best_ratio, 3),
                    node_id=best_node.id,
                    canonical_name=best_node.name,
                    entity_type=best_node.node_type,
                    reason=f"Fuzzy string similarity {best_ratio:.2f} >= threshold {fuzzy_threshold} with '{best_node.name}'."
                )

        # No match found
        return None, ResolutionResult(
            matched=False,
            strategy="no_match",
            confidence=0.0,
            canonical_name=canonical_name,
            entity_type=resolved_type,
            reason="No existing node in workspace satisfied resolution criteria."
        )

    def resolve_or_create_node(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        extracted: ExtractedEntity,
        allow_fuzzy: bool = True
    ) -> KnowledgeGraphNode:
        """
        Idempotently resolves an entity mention to an existing node in the workspace or inserts a new node.
        Updates provenance metadata upon resolution to prevent duplicate entities.
        """
        existing_node, resolution = self.resolve_entity(
            user_id=user_id,
            workspace_id=workspace_id,
            extracted=extracted,
            allow_fuzzy=allow_fuzzy
        )

        canonical_name, lookup_key, resolved_type = EntityNormalizer.canonicalize(
            extracted.name, fallback_type=extracted.entity_type
        )

        if existing_node:
            # Update description or metadata if previously empty
            updated = False
            if not existing_node.description and extracted.description:
                existing_node.description = extracted.description
                updated = True
            
            # Enrich provenance metadata
            current_meta = dict(existing_node.meta_data or {})
            provenance_list = current_meta.get("provenance", [])
            if extracted.chunk_id and str(extracted.chunk_id) not in [p.get("chunk_id") for p in provenance_list]:
                provenance_list.append({
                    "document_id": str(extracted.document_id) if extracted.document_id else None,
                    "chunk_id": str(extracted.chunk_id) if extracted.chunk_id else None,
                    "page_number": extracted.page_number,
                    "section_title": extracted.section_title
                })
                current_meta["provenance"] = provenance_list[:30] # Bounded provenance list
                existing_node.meta_data = current_meta
                updated = True

            # Track resolved aliases in metadata
            aliases = set(current_meta.get("aliases", []))
            if extracted.name and extracted.name != existing_node.name:
                aliases.add(extracted.name)
                current_meta["aliases"] = list(aliases)[:15]
                existing_node.meta_data = current_meta
                updated = True

            if updated:
                self.db.commit()
                self.db.refresh(existing_node)
            return existing_node

        # 2. Node does not exist - create new node
        meta_payload: Dict[str, Any] = {
            "canonical_key": lookup_key,
            "aliases": [extracted.name] if extracted.name != canonical_name else [],
            "provenance": [{
                "document_id": str(extracted.document_id) if extracted.document_id else None,
                "chunk_id": str(extracted.chunk_id) if extracted.chunk_id else None,
                "page_number": extracted.page_number,
                "section_title": extracted.section_title
            }] if extracted.chunk_id else []
        }

        new_node = self.kg_service.create_node(
            user_id=user_id,
            workspace_id=workspace_id,
            node_data=NodeCreate(
                node_type=resolved_type,
                name=canonical_name,
                description=extracted.description,
                metadata=meta_payload
            )
        )
        return new_node

    def merge_duplicate_nodes(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID
    ) -> Optional[KnowledgeGraphNode]:
        """
        Safely merges a redundant duplicate node (source) into a canonical node (target).
        Transfers all edges, merges provenance, metadata, and aliases, then deletes source node.
        Strictly bounded to the tenant workspace.
        """
        if source_node_id == target_node_id:
            return None

        source_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.id == source_node_id,
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).first()

        target_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.id == target_node_id,
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).first()

        if not source_node or not target_node:
            logger.warning("Merge aborted: source or target node not found in tenant workspace.")
            return None

        # 1. Reroute outbound edges
        out_edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.source_node_id == source_node.id,
            KnowledgeGraphEdge.workspace_id == workspace_id
        ).all()
        for edge in out_edges:
            if edge.target_node_id != target_node.id:
                # Check if target already has an equivalent edge
                exists = self.db.query(KnowledgeGraphEdge).filter(
                    KnowledgeGraphEdge.source_node_id == target_node.id,
                    KnowledgeGraphEdge.target_node_id == edge.target_node_id,
                    KnowledgeGraphEdge.relationship_type == edge.relationship_type,
                    KnowledgeGraphEdge.workspace_id == workspace_id
                ).first()
                if not exists:
                    edge.source_node_id = target_node.id
                else:
                    self.db.delete(edge)
            else:
                self.db.delete(edge)

        # 2. Reroute inbound edges
        in_edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.target_node_id == source_node.id,
            KnowledgeGraphEdge.workspace_id == workspace_id
        ).all()
        for edge in in_edges:
            if edge.source_node_id != target_node.id:
                exists = self.db.query(KnowledgeGraphEdge).filter(
                    KnowledgeGraphEdge.source_node_id == edge.source_node_id,
                    KnowledgeGraphEdge.target_node_id == target_node.id,
                    KnowledgeGraphEdge.relationship_type == edge.relationship_type,
                    KnowledgeGraphEdge.workspace_id == workspace_id
                ).first()
                if not exists:
                    edge.target_node_id = target_node.id
                else:
                    self.db.delete(edge)
            else:
                self.db.delete(edge)

        # 3. Merge Metadata & Provenance
        s_meta = dict(source_node.meta_data or {})
        t_meta = dict(target_node.meta_data or {})

        # Merge Aliases
        merged_aliases = set(t_meta.get("aliases", []))
        merged_aliases.update(s_meta.get("aliases", []))
        merged_aliases.add(source_node.name)
        if target_node.name in merged_aliases:
            merged_aliases.remove(target_node.name)
        t_meta["aliases"] = list(merged_aliases)[:20]

        # Merge Provenance
        merged_prov = list(t_meta.get("provenance", []))
        existing_chunk_ids = {p.get("chunk_id") for p in merged_prov if p.get("chunk_id")}
        for prov in s_meta.get("provenance", []):
            if prov.get("chunk_id") not in existing_chunk_ids:
                merged_prov.append(prov)
                existing_chunk_ids.add(prov.get("chunk_id"))
        t_meta["provenance"] = merged_prov[:30]

        target_node.meta_data = t_meta

        # Preserve richer description
        if not target_node.description and source_node.description:
            target_node.description = source_node.description

        # 4. Delete source node
        self.db.delete(source_node)
        self.db.commit()
        self.db.refresh(target_node)

        logger.info(f"Merged duplicate node {source_node.name} ({source_node.id}) into {target_node.name} ({target_node.id})")
        return target_node
