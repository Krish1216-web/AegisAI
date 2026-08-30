import uuid
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from loguru import logger

from app.models.document import Document, DocumentChunk
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.entity_extraction import (
    EntityExtractionFactory,
    EntityResolver,
    RelationshipExtractor,
    BaseEntityExtractor,
    ExtractionResult
)
from app.schemas.knowledge_graph import NodeCreate, EdgeCreate, NodeResponse, EdgeResponse

class GraphConstructionService:
    """
    Orchestrates the conversion of Document and DocumentChunk text into structured
    KnowledgeGraphNode and KnowledgeGraphEdge records.
    """
    def __init__(self, db: Session, extractor: Optional[BaseEntityExtractor] = None):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)
        self.extractor = extractor or EntityExtractionFactory.get_extractor(provider="rule_based")
        self.resolver = EntityResolver(db)
        self.rel_extractor = RelationshipExtractor(db)

    def construct_graph_from_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Extracts entities and builds the complete knowledge graph representation for an entire document.
        Idempotent: Reuses existing nodes and edge relationships without creating duplicates.
        """
        start_time = time.perf_counter()
        doc = self.db.query(Document).filter(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
            Document.user_id == user_id
        ).first()

        if not doc:
            raise ValueError(f"Document {document_id} not found in workspace.")

        # 1. Ensure Document Root Node exists
        doc_node = self.kg_service.get_node_by_external_id(
            user_id=user_id,
            workspace_id=workspace_id,
            external_id=f"doc_{doc.id}"
        )
        if not doc_node:
            doc_node = self.kg_service.create_node(
                user_id=user_id,
                workspace_id=workspace_id,
                node_data=NodeCreate(
                    node_type=NodeType.DOCUMENT.value,
                    name=doc.original_filename,
                    external_id=f"doc_{doc.id}",
                    description=f"Uploaded {doc.file_extension} document ({doc.file_size} bytes)",
                    metadata={
                        "document_id": str(doc.id),
                        "mime_type": doc.mime_type,
                        "page_count": doc.page_count
                    }
                )
            )

        chunks = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.workspace_id == workspace_id,
            DocumentChunk.user_id == user_id
        ).order_by(DocumentChunk.chunk_index).all()

        nodes_created = 0
        edges_created = 0
        total_entities_extracted = 0

        # 2. Process each chunk
        for chunk in chunks:
            # A. Ensure Chunk Node exists
            chunk_node = self.kg_service.get_node_by_external_id(
                user_id=user_id,
                workspace_id=workspace_id,
                external_id=f"chunk_{chunk.id}"
            )
            if not chunk_node:
                chunk_node = self.kg_service.create_node(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    node_data=NodeCreate(
                        node_type=NodeType.DOCUMENT_CHUNK.value,
                        name=f"{doc.original_filename} [Chunk #{chunk.chunk_index}]",
                        external_id=f"chunk_{chunk.id}",
                        description=chunk.content[:200] if chunk.content else "",
                        metadata={
                            "document_id": str(doc.id),
                            "chunk_id": str(chunk.id),
                            "chunk_index": chunk.chunk_index,
                            "page_number": chunk.page_number,
                            "section_title": chunk.section_title
                        }
                    )
                )
                nodes_created += 1

            # Connect Document -> CONTAINS -> Chunk
            edge_doc_chunk = self.db.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id,
                KnowledgeGraphEdge.source_node_id == doc_node.id,
                KnowledgeGraphEdge.target_node_id == chunk_node.id,
                KnowledgeGraphEdge.relationship_type == RelationshipType.CONTAINS.value
            ).first()
            if not edge_doc_chunk:
                self.kg_service.create_edge(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    edge_data=EdgeCreate(
                        source_node_id=doc_node.id,
                        target_node_id=chunk_node.id,
                        relationship_type=RelationshipType.CONTAINS.value,
                        confidence=1.0
                    )
                )
                edges_created += 1

            # B. Extract Entities & Relationships from Chunk Text
            extraction: ExtractionResult = self.extractor.extract(
                text=chunk.content,
                document_id=doc.id,
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                section_title=chunk.section_title
            )

            resolved_nodes: Dict[str, KnowledgeGraphNode] = {}

            # Resolve/Create Entity Nodes
            for ext_ent in extraction.entities:
                total_entities_extracted += 1
                ent_node = self.resolver.resolve_or_create_node(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    extracted=ext_ent
                )
                resolved_nodes[ext_ent.name] = ent_node

                # Link Chunk -> MENTIONS/REFERENCES -> Entity Node
                edge_chunk_ent = self.db.query(KnowledgeGraphEdge).filter(
                    KnowledgeGraphEdge.workspace_id == workspace_id,
                    KnowledgeGraphEdge.user_id == user_id,
                    KnowledgeGraphEdge.source_node_id == chunk_node.id,
                    KnowledgeGraphEdge.target_node_id == ent_node.id
                ).first()
                if not edge_chunk_ent:
                    self.kg_service.create_edge(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        edge_data=EdgeCreate(
                            source_node_id=chunk_node.id,
                            target_node_id=ent_node.id,
                            relationship_type=RelationshipType.REFERENCES.value,
                            confidence=ext_ent.confidence,
                            properties={"chunk_id": str(chunk.id), "page": chunk.page_number}
                        )
                    )
                    edges_created += 1

            # Persist Extracted Relationships between entity nodes
            for ext_rel in extraction.relationships:
                src_node = resolved_nodes.get(ext_rel.source_entity_name)
                tgt_node = resolved_nodes.get(ext_rel.target_entity_name)
                if src_node and tgt_node:
                    edge = self.rel_extractor.persist_relationship(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        source_node=src_node,
                        target_node=tgt_node,
                        rel=ext_rel
                    )
                    if edge:
                        edges_created += 1

        elapsed = time.perf_counter() - start_time
        logger.info(f"Graph construction completed for doc {document_id}: {total_entities_extracted} entities processed, {edges_created} edges formed in {elapsed:.2f}s")

        return {
            "document_id": str(document_id),
            "chunks_processed": len(chunks),
            "entities_extracted": total_entities_extracted,
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "execution_time": round(elapsed, 4),
            "status": "completed"
        }

    def rebuild_document_graph(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Safely rebuilds the knowledge graph for a document by clearing existing chunk edges and re-extracting.
        """
        # Delete existing chunk nodes for this document
        doc_node = self.kg_service.get_node_by_external_id(
            user_id=user_id,
            workspace_id=workspace_id,
            external_id=f"doc_{document_id}"
        )
        if doc_node:
            # Find chunk nodes
            chunk_edges = self.db.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id,
                KnowledgeGraphEdge.source_node_id == doc_node.id,
                KnowledgeGraphEdge.relationship_type == RelationshipType.CONTAINS.value
            ).all()
            for ce in chunk_edges:
                self.kg_service.delete_node(user_id=user_id, workspace_id=workspace_id, node_id=ce.target_node_id)

        return self.construct_graph_from_document(
            document_id=document_id,
            user_id=user_id,
            workspace_id=workspace_id
        )

    def get_document_entities(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> List[NodeResponse]:
        """
        Retrieves all Knowledge Graph entities connected to this document.
        """
        doc_node = self.kg_service.get_node_by_external_id(
            user_id=user_id,
            workspace_id=workspace_id,
            external_id=f"doc_{document_id}"
        )
        if not doc_node:
            return []

        # Find 1-hop and 2-hop connected entity nodes
        chunk_edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            KnowledgeGraphEdge.source_node_id == doc_node.id
        ).all()

        chunk_ids = [ce.target_node_id for ce in chunk_edges]
        if not chunk_ids:
            return [NodeResponse.model_validate(doc_node)]

        entity_edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            KnowledgeGraphEdge.source_node_id.in_(chunk_ids)
        ).all()

        all_node_ids = set([doc_node.id] + chunk_ids + [ee.target_node_id for ee in entity_edges])
        nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.id.in_(all_node_ids),
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).all()

        return [NodeResponse.model_validate(n) for n in nodes]

    def get_document_relationships(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> List[EdgeResponse]:
        """
        Retrieves all Knowledge Graph edge relationships belonging to this document and its extracted entities.
        """
        entities = self.get_document_entities(document_id, user_id, workspace_id)
        if not entities:
            return []

        node_ids = [e.id for e in entities]
        edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            or_(
                KnowledgeGraphEdge.source_node_id.in_(node_ids),
                KnowledgeGraphEdge.target_node_id.in_(node_ids)
            )
        ).all()

        return [EdgeResponse.model_validate(e) for e in edges]
