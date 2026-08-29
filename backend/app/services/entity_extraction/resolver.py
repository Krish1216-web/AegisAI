import uuid
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.knowledge_graph import KnowledgeGraphNode
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.entity_extraction.models import ExtractedEntity
from app.services.entity_extraction.normalizer import EntityNormalizer
from app.schemas.knowledge_graph import NodeCreate

class EntityResolver:
    """
    Resolves extracted entity mentions to existing tenant Knowledge Graph nodes or creates new ones.
    Strictly enforces workspace and user isolation.
    """
    def __init__(self, db: Session):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)

    def resolve_or_create_node(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        extracted: ExtractedEntity
    ) -> KnowledgeGraphNode:
        """
        Idempotently resolves an entity mention to an existing node in the workspace or inserts a new node.
        """
        canonical_name, lookup_key, resolved_type = EntityNormalizer.canonicalize(
            extracted.name, fallback_type=extracted.entity_type
        )

        # 1. Search for existing node in workspace with matching name (case-insensitive) or external_id
        existing_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id,
            func.lower(KnowledgeGraphNode.name) == canonical_name.lower()
        ).first()

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
                current_meta["provenance"] = provenance_list[:20] # Bound provenance list
                existing_node.meta_data = current_meta
                updated = True

            if updated:
                self.db.commit()
                self.db.refresh(existing_node)
            return existing_node

        # 2. Node does not exist - create new node
        meta_payload: Dict[str, Any] = {
            "canonical_key": lookup_key,
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
