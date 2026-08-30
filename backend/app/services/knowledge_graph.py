import uuid
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import deque
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from loguru import logger

from app.core.exceptions import AegisBaseException
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.schemas.knowledge_graph import NodeCreate, NodeUpdate, EdgeCreate
from app.models.document import Document
from app.models.memory import AgentMemory

class NodeNotFound(AegisBaseException):
    def __init__(self, message: str = "The requested knowledge graph node was not found.", details: Any = None):
        super().__init__(message, code="NODE_NOT_FOUND", details=details)

class EdgeNotFound(AegisBaseException):
    def __init__(self, message: str = "The requested knowledge graph edge was not found.", details: Any = None):
        super().__init__(message, code="EDGE_NOT_FOUND", details=details)

class CrossTenantEdgeError(AegisBaseException):
    def __init__(self, message: str = "Cannot connect nodes across different tenant or workspace boundaries.", details: Any = None):
        super().__init__(message, code="PERMISSION_DENIED", details=details)

class DuplicateEdgeError(AegisBaseException):
    def __init__(self, message: str = "An identical edge relationship already exists between these nodes.", details: Any = None):
        super().__init__(message, code="DUPLICATE_EDGE", details=details)

class KnowledgeGraphService:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # Node Operations
    # ---------------------------------------------------------

    def create_node(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_data: NodeCreate
    ) -> KnowledgeGraphNode:
        node = KnowledgeGraphNode(
            user_id=user_id,
            workspace_id=workspace_id,
            node_type=node_data.node_type,
            external_id=node_data.external_id,
            name=node_data.name,
            description=node_data.description,
            meta_data=node_data.metadata
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_node(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_id: uuid.UUID
    ) -> Optional[KnowledgeGraphNode]:
        return self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.id == node_id,
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).first()

    def get_node_by_external_id(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        external_id: str
    ) -> Optional[KnowledgeGraphNode]:
        return self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.external_id == external_id,
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).first()

    def update_node(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_id: uuid.UUID,
        update_data: NodeUpdate
    ) -> KnowledgeGraphNode:
        node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=node_id)
        if not node:
            raise NodeNotFound(f"Node {node_id} not found in this workspace.")

        if update_data.name is not None:
            node.name = update_data.name
        if update_data.description is not None:
            node.description = update_data.description
        if update_data.metadata is not None:
            node.meta_data = update_data.metadata

        self.db.commit()
        self.db.refresh(node)
        return node

    def delete_node(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_id: uuid.UUID
    ) -> bool:
        node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=node_id)
        if not node:
            raise NodeNotFound(f"Node {node_id} not found in this workspace.")

        self.db.delete(node)
        self.db.commit()
        return True

    def list_nodes(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_type: Optional[str] = None,
        external_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[KnowledgeGraphNode], int]:
        filters = [
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ]
        if node_type:
            filters.append(KnowledgeGraphNode.node_type == node_type)
        if external_id:
            filters.append(KnowledgeGraphNode.external_id == external_id)

        total = self.db.query(func.count(KnowledgeGraphNode.id)).filter(*filters).scalar() or 0
        nodes = (
            self.db.query(KnowledgeGraphNode)
            .filter(*filters)
            .order_by(KnowledgeGraphNode.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return nodes, total

    # ---------------------------------------------------------
    # Edge Operations
    # ---------------------------------------------------------

    def create_edge(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        edge_data: EdgeCreate
    ) -> KnowledgeGraphEdge:
        # 1. Verify source node exists and belongs to the active tenant
        source_node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=edge_data.source_node_id)
        if not source_node:
            raise NodeNotFound(f"Source node {edge_data.source_node_id} not found in workspace.")

        # 2. Verify target node exists and belongs to the active tenant
        target_node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=edge_data.target_node_id)
        if not target_node:
            raise NodeNotFound(f"Target node {edge_data.target_node_id} not found in workspace.")

        # 3. Check for existing edge
        existing = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.source_node_id == edge_data.source_node_id,
            KnowledgeGraphEdge.target_node_id == edge_data.target_node_id,
            KnowledgeGraphEdge.relationship_type == edge_data.relationship_type
        ).first()

        if existing:
            raise DuplicateEdgeError(
                f"Edge '{edge_data.relationship_type}' already connects {edge_data.source_node_id} -> {edge_data.target_node_id}."
            )

        edge = KnowledgeGraphEdge(
            user_id=user_id,
            workspace_id=workspace_id,
            source_node_id=edge_data.source_node_id,
            target_node_id=edge_data.target_node_id,
            relationship_type=edge_data.relationship_type,
            confidence=edge_data.confidence,
            meta_data=edge_data.properties
        )
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge

    def get_edge(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        edge_id: uuid.UUID
    ) -> Optional[KnowledgeGraphEdge]:
        return self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.id == edge_id,
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id
        ).first()

    def delete_edge(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        edge_id: uuid.UUID
    ) -> bool:
        edge = self.get_edge(user_id=user_id, workspace_id=workspace_id, edge_id=edge_id)
        if not edge:
            raise EdgeNotFound(f"Edge {edge_id} not found in workspace.")

        self.db.delete(edge)
        self.db.commit()
        return True

    def list_edges(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_node_id: Optional[uuid.UUID] = None,
        target_node_id: Optional[uuid.UUID] = None,
        relationship_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[KnowledgeGraphEdge], int]:
        filters = [
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id
        ]
        if source_node_id:
            filters.append(KnowledgeGraphEdge.source_node_id == source_node_id)
        if target_node_id:
            filters.append(KnowledgeGraphEdge.target_node_id == target_node_id)
        if relationship_type:
            filters.append(KnowledgeGraphEdge.relationship_type == relationship_type)

        total = self.db.query(func.count(KnowledgeGraphEdge.id)).filter(*filters).scalar() or 0
        edges = (
            self.db.query(KnowledgeGraphEdge)
            .filter(*filters)
            .order_by(KnowledgeGraphEdge.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return edges, total

    # ---------------------------------------------------------
    # Neighbor & Traversal Operations
    # ---------------------------------------------------------

    def get_neighbors(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_id: uuid.UUID,
        relationship_types: Optional[List[str]] = None,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        center_node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=node_id)
        if not center_node:
            raise NodeNotFound(f"Node {node_id} not found.")

        neighbors: List[Dict[str, Any]] = []

        # Outgoing edges
        if direction in ("both", "outgoing"):
            out_query = self.db.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.source_node_id == node_id,
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id
            )
            if relationship_types:
                out_query = out_query.filter(KnowledgeGraphEdge.relationship_type.in_(relationship_types))
            for edge in out_query.all():
                target = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=edge.target_node_id)
                if target:
                    neighbors.append({
                        "node": target,
                        "relationship_type": edge.relationship_type,
                        "direction": "outgoing",
                        "confidence": edge.confidence,
                        "edge_id": edge.id
                    })

        # Incoming edges
        if direction in ("both", "incoming"):
            in_query = self.db.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.target_node_id == node_id,
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id
            )
            if relationship_types:
                in_query = in_query.filter(KnowledgeGraphEdge.relationship_type.in_(relationship_types))
            for edge in in_query.all():
                source = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=edge.source_node_id)
                if source:
                    neighbors.append({
                        "node": source,
                        "relationship_type": edge.relationship_type,
                        "direction": "incoming",
                        "confidence": edge.confidence,
                        "edge_id": edge.id
                    })

        return neighbors

    def traverse(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        start_node_ids: List[uuid.UUID],
        max_depth: int = 3,
        relationship_types: Optional[List[str]] = None,
        node_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        # Guardrails: safe traversal limits
        clamped_depth = min(max(1, max_depth), 5)
        clamped_limit = min(max(1, limit), 500)

        visited_nodes: Set[uuid.UUID] = set()
        visited_edges: Set[uuid.UUID] = set()
        
        result_nodes: Dict[uuid.UUID, KnowledgeGraphNode] = {}
        result_edges: Dict[uuid.UUID, KnowledgeGraphEdge] = {}

        queue: deque = deque()
        depth_reached = 0

        # Initialize BFS queue
        for start_id in start_node_ids:
            node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=start_id)
            if node:
                if not node_types or node.node_type in node_types:
                    result_nodes[node.id] = node
                visited_nodes.add(node.id)
                queue.append((node.id, 0))

        while queue and len(result_nodes) < clamped_limit:
            current_id, current_depth = queue.popleft()
            depth_reached = max(depth_reached, current_depth)

            if current_depth >= clamped_depth:
                continue

            # Fetch edges connected to current_id in this tenant
            edge_filters = [
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id,
                or_(
                    KnowledgeGraphEdge.source_node_id == current_id,
                    KnowledgeGraphEdge.target_node_id == current_id
                )
            ]
            if relationship_types:
                edge_filters.append(KnowledgeGraphEdge.relationship_type.in_(relationship_types))

            connected_edges = self.db.query(KnowledgeGraphEdge).filter(*edge_filters).all()

            for edge in connected_edges:
                next_node_id = edge.target_node_id if edge.source_node_id == current_id else edge.source_node_id

                # Record edge
                if edge.id not in visited_edges:
                    visited_edges.add(edge.id)
                    result_edges[edge.id] = edge

                # Visit adjacent node if not seen
                if next_node_id not in visited_nodes:
                    visited_nodes.add(next_node_id)
                    next_node = self.get_node(user_id=user_id, workspace_id=workspace_id, node_id=next_node_id)
                    if next_node:
                        if not node_types or next_node.node_type in node_types:
                            result_nodes[next_node.id] = next_node
                        
                        queue.append((next_node.id, current_depth + 1))

                        if len(result_nodes) >= clamped_limit:
                            break

        return {
            "nodes": list(result_nodes.values()),
            "edges": list(result_edges.values()),
            "depth_reached": depth_reached,
            "total_nodes": len(result_nodes),
            "total_edges": len(result_edges)
        }

    # ---------------------------------------------------------
    # Search
    # ---------------------------------------------------------

    def search_nodes(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        query: str,
        node_type: Optional[str] = None,
        limit: int = 20
    ) -> List[KnowledgeGraphNode]:
        filters = [
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ]
        if node_type:
            filters.append(KnowledgeGraphNode.node_type == node_type)

        search_pattern = f"%{query}%"
        filters.append(
            or_(
                KnowledgeGraphNode.name.ilike(search_pattern),
                KnowledgeGraphNode.description.ilike(search_pattern)
            )
        )

        return (
            self.db.query(KnowledgeGraphNode)
            .filter(*filters)
            .limit(limit)
            .all()
        )

    # ---------------------------------------------------------
    # Document & Memory Integration Helpers
    # ---------------------------------------------------------

    def sync_document_graph(self, document: Document) -> List[KnowledgeGraphNode]:
        """
        Creates/updates graph nodes and edges representing the Document and its Chunks.
        """
        created_nodes: List[KnowledgeGraphNode] = []
        user_id = document.user_id
        workspace_id = document.workspace_id

        # 1. Document Node
        doc_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.node_type == NodeType.DOCUMENT.value,
            KnowledgeGraphNode.external_id == str(document.id)
        ).first()

        if not doc_node:
            doc_node = KnowledgeGraphNode(
                user_id=user_id,
                workspace_id=workspace_id,
                node_type=NodeType.DOCUMENT.value,
                external_id=str(document.id),
                name=document.original_filename,
                description=f"File {document.filename} ({document.mime_type}, {document.file_size} bytes)",
                meta_data={"mime_type": document.mime_type, "file_size": document.file_size}
            )
            self.db.add(doc_node)
            self.db.flush()
        created_nodes.append(doc_node)

        # 2. Workspace Node & Edge
        ws_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.node_type == NodeType.WORKSPACE.value,
            KnowledgeGraphNode.external_id == str(workspace_id)
        ).first()

        if not ws_node:
            ws_node = KnowledgeGraphNode(
                user_id=user_id,
                workspace_id=workspace_id,
                node_type=NodeType.WORKSPACE.value,
                external_id=str(workspace_id),
                name="Workspace Node",
                description="Workspace tenant entity"
            )
            self.db.add(ws_node)
            self.db.flush()

        # Edge: Document -> BELONGS_TO -> Workspace
        existing_ws_edge = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.source_node_id == doc_node.id,
            KnowledgeGraphEdge.target_node_id == ws_node.id,
            KnowledgeGraphEdge.relationship_type == RelationshipType.BELONGS_TO.value
        ).first()
        if not existing_ws_edge:
            self.db.add(KnowledgeGraphEdge(
                user_id=user_id,
                workspace_id=workspace_id,
                source_node_id=doc_node.id,
                target_node_id=ws_node.id,
                relationship_type=RelationshipType.BELONGS_TO.value,
                confidence=1.0
            ))

        # 3. User Node & Edge
        user_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.node_type == NodeType.USER.value,
            KnowledgeGraphNode.external_id == str(user_id)
        ).first()

        if not user_node:
            user_node = KnowledgeGraphNode(
                user_id=user_id,
                workspace_id=workspace_id,
                node_type=NodeType.USER.value,
                external_id=str(user_id),
                name="User Node",
                description="User entity"
            )
            self.db.add(user_node)
            self.db.flush()

        # Edge: Document -> CREATED_BY -> User
        existing_user_edge = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.source_node_id == doc_node.id,
            KnowledgeGraphEdge.target_node_id == user_node.id,
            KnowledgeGraphEdge.relationship_type == RelationshipType.CREATED_BY.value
        ).first()
        if not existing_user_edge:
            self.db.add(KnowledgeGraphEdge(
                user_id=user_id,
                workspace_id=workspace_id,
                source_node_id=doc_node.id,
                target_node_id=user_node.id,
                relationship_type=RelationshipType.CREATED_BY.value,
                confidence=1.0
            ))

        # 4. Chunk Nodes & Edges
        if document.chunks:
            for chunk in document.chunks:
                chunk_node = self.db.query(KnowledgeGraphNode).filter(
                    KnowledgeGraphNode.workspace_id == workspace_id,
                    KnowledgeGraphNode.node_type == NodeType.DOCUMENT_CHUNK.value,
                    KnowledgeGraphNode.external_id == str(chunk.id)
                ).first()

                if not chunk_node:
                    chunk_node = KnowledgeGraphNode(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        node_type=NodeType.DOCUMENT_CHUNK.value,
                        external_id=str(chunk.id),
                        name=f"Chunk {chunk.chunk_index}: {document.original_filename}",
                        description=chunk.content[:200],
                        meta_data={
                            "chunk_index": chunk.chunk_index,
                            "page_number": chunk.page_number,
                            "section_title": chunk.section_title
                        }
                    )
                    self.db.add(chunk_node)
                    self.db.flush()
                created_nodes.append(chunk_node)

                # Edge: Document -> CONTAINS -> Chunk
                existing_chunk_edge = self.db.query(KnowledgeGraphEdge).filter(
                    KnowledgeGraphEdge.source_node_id == doc_node.id,
                    KnowledgeGraphEdge.target_node_id == chunk_node.id,
                    KnowledgeGraphEdge.relationship_type == RelationshipType.CONTAINS.value
                ).first()
                if not existing_chunk_edge:
                    self.db.add(KnowledgeGraphEdge(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        source_node_id=doc_node.id,
                        target_node_id=chunk_node.id,
                        relationship_type=RelationshipType.CONTAINS.value,
                        confidence=1.0
                    ))

        self.db.commit()
        return created_nodes

    def sync_memory_graph(self, memory: AgentMemory) -> KnowledgeGraphNode:
        """
        Creates/updates graph node and edge representing an AgentMemory record.
        """
        user_id = memory.user_id
        workspace_id = memory.workspace_id

        mem_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.node_type == NodeType.MEMORY.value,
            KnowledgeGraphNode.external_id == str(memory.id)
        ).first()

        if not mem_node:
            mem_node = KnowledgeGraphNode(
                user_id=user_id,
                workspace_id=workspace_id,
                node_type=NodeType.MEMORY.value,
                external_id=str(memory.id),
                name=f"Memory: {memory.memory_type}",
                description=memory.content[:200] if memory.content else None,
                meta_data={
                    "memory_type": memory.memory_type,
                    "importance": memory.importance,
                    "confidence": memory.confidence
                }
            )
            self.db.add(mem_node)
            self.db.flush()

        # Connect to User
        user_node = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.node_type == NodeType.USER.value,
            KnowledgeGraphNode.external_id == str(user_id)
        ).first()

        if not user_node:
            user_node = KnowledgeGraphNode(
                user_id=user_id,
                workspace_id=workspace_id,
                node_type=NodeType.USER.value,
                external_id=str(user_id),
                name="User Node",
                description="User entity"
            )
            self.db.add(user_node)
            self.db.flush()

        existing_edge = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.source_node_id == mem_node.id,
            KnowledgeGraphEdge.target_node_id == user_node.id,
            KnowledgeGraphEdge.relationship_type == RelationshipType.BELONGS_TO.value
        ).first()
        if not existing_edge:
            self.db.add(KnowledgeGraphEdge(
                user_id=user_id,
                workspace_id=workspace_id,
                source_node_id=mem_node.id,
                target_node_id=user_node.id,
                relationship_type=RelationshipType.BELONGS_TO.value,
                confidence=1.0
            ))

        self.db.commit()
        return mem_node

    # ---------------------------------------------------------
    # RAG Graph-Context Preparation
    # ---------------------------------------------------------

    def get_graph_context(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_ids: List[uuid.UUID],
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Retrieves structured subgraph context surrounding node_ids for injection into RAG prompt.
        """
        traversal = self.traverse(
            user_id=user_id,
            workspace_id=workspace_id,
            start_node_ids=node_ids,
            max_depth=max_depth,
            limit=50
        )

        entities = []
        for n in traversal["nodes"]:
            entities.append({
                "id": str(n.id),
                "type": n.node_type,
                "name": n.name,
                "description": n.description or ""
            })

        relationships = []
        node_lookup = {n.id: n.name for n in traversal["nodes"]}
        for e in traversal["edges"]:
            src_name = node_lookup.get(e.source_node_id, str(e.source_node_id))
            tgt_name = node_lookup.get(e.target_node_id, str(e.target_node_id))
            relationships.append({
                "source": src_name,
                "target": tgt_name,
                "relationship": e.relationship_type,
                "confidence": e.confidence
            })

        # Format human/LLM-readable text context
        entity_lines = [f"- [{e['type']}] {e['name']}: {e['description']}" for e in entities]
        rel_lines = [f"- {r['source']} -> [{r['relationship']}] -> {r['target']} (confidence: {r['confidence']})" for r in relationships]

        formatted = "Knowledge Graph Entities:\n" + ("\n".join(entity_lines) if entity_lines else "None")
        formatted += "\n\nKnowledge Graph Relationships:\n" + ("\n".join(rel_lines) if rel_lines else "None")

        return {
            "entities": entities,
            "relationships": relationships,
            "formatted_context": formatted
        }
