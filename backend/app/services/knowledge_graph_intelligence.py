import uuid
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import deque
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from loguru import logger

from app.core.exceptions import AegisBaseException
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService, NodeNotFound, EdgeNotFound
from app.schemas.knowledge_graph import (
    NodeResponse,
    RelatedEntityItem,
    RelatedEntitiesResponse,
    GraphPathStep,
    GraphPathResponse,
    RelationshipDetail,
    RelationshipAnalysisResponse
)

# Relationship importance weightings for deterministic relevance ranking
RELATIONSHIP_WEIGHTS: Dict[str, float] = {
    RelationshipType.CONTAINS.value: 1.0,
    RelationshipType.PART_OF.value: 1.0,
    RelationshipType.DEPENDS_ON.value: 0.95,
    RelationshipType.OWNS.value: 0.90,
    RelationshipType.BELONGS_TO.value: 0.90,
    RelationshipType.ASSIGNED_TO.value: 0.85,
    RelationshipType.EXECUTED.value: 0.85,
    RelationshipType.USES.value: 0.85,
    RelationshipType.RELATED_TO.value: 0.80,
    RelationshipType.REFERENCES.value: 0.80,
    RelationshipType.HAS_MEMORY.value: 0.75,
    RelationshipType.CREATED_BY.value: 0.75,
    RelationshipType.WORKS_ON.value: 0.75,
    RelationshipType.MENTIONS.value: 0.70,
}

NODE_TYPE_WEIGHTS: Dict[str, float] = {
    NodeType.DOCUMENT.value: 1.0,
    NodeType.DOCUMENT_CHUNK.value: 0.95,
    NodeType.PROJECT.value: 0.95,
    NodeType.MEMORY.value: 0.90,
    NodeType.TASK.value: 0.85,
    NodeType.SKILL.value: 0.85,
    NodeType.AGENT.value: 0.80,
    NodeType.CONVERSATION.value: 0.75,
    NodeType.WORKSPACE.value: 0.70,
    NodeType.USER.value: 0.70,
}

class KnowledgeGraphIntelligenceService:
    """
    Intelligent graph analysis, multi-hop pathfinding, relevance ranking,
    and grounded context builder for RAG and multi-agent execution.
    """
    def __init__(self, db: Session):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)

    # ---------------------------------------------------------
    # 1. Deterministic Graph Relevance Scoring
    # ---------------------------------------------------------

    def calculate_relevance_score(
        self,
        distance: int,
        path_confidence: float,
        rel_types: List[str],
        node_type: str
    ) -> float:
        """
        Computes an explainable, bounded, deterministic relevance score in range [0.0, 1.0].
        
        Formula components:
        - Distance Decay: 1 / (1 + distance * 0.4)
        - Path Confidence: product of edge confidences along the shortest path
        - Relationship Priority: average weight of relationships in path
        - Node Type Priority: weight of the target entity type
        """
        if distance <= 0:
            return 1.0

        # Distance factor (1 -> 0.714, 2 -> 0.555, 3 -> 0.454, 4 -> 0.384, 5 -> 0.333)
        dist_factor = 1.0 / (1.0 + (distance * 0.4))

        # Relationship weights
        if rel_types:
            avg_rel_weight = sum(RELATIONSHIP_WEIGHTS.get(r, 0.75) for r in rel_types) / len(rel_types)
        else:
            avg_rel_weight = 0.75

        # Node type weight
        node_weight = NODE_TYPE_WEIGHTS.get(node_type, 0.8)

        raw_score = dist_factor * path_confidence * avg_rel_weight * node_weight
        # Normalize and clamp
        score = max(0.0, min(1.0, raw_score))
        return round(score, 4)

    # ---------------------------------------------------------
    # 2. Related Entity Discovery
    # ---------------------------------------------------------

    def get_related_entities(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_id: uuid.UUID,
        depth: int = 2,
        limit: int = 50,
        relationship_types: Optional[List[str]] = None,
        node_types: Optional[List[str]] = None
    ) -> RelatedEntitiesResponse:
        """
        Discovers and ranks all entities connected to the specified node within the tenant workspace.
        """
        root_node = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=node_id)
        if not root_node:
            raise NodeNotFound(f"Node {node_id} not found in workspace.")

        max_depth = max(1, min(depth, 5))
        max_limit = max(1, min(limit, 500))

        # BFS state tracking
        # queue item: (current_node_id, current_depth, path_confidence, rel_path)
        queue: deque = deque([(node_id, 0, 1.0, [])])
        visited: Dict[uuid.UUID, Tuple[int, float, List[str]]] = {
            node_id: (0, 1.0, [])
        }

        # Collect candidate related nodes
        discovered_nodes: Dict[uuid.UUID, KnowledgeGraphNode] = {}

        while queue:
            curr_id, curr_depth, curr_conf, curr_path = queue.popleft()

            if curr_depth >= max_depth:
                continue

            # Fetch edges connected to curr_id (both outgoing and incoming)
            edges_query = self.db.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id,
                or_(
                    KnowledgeGraphEdge.source_node_id == curr_id,
                    KnowledgeGraphEdge.target_node_id == curr_id
                )
            )
            if relationship_types:
                edges_query = edges_query.filter(KnowledgeGraphEdge.relationship_type.in_(relationship_types))

            edges = edges_query.all()

            for edge in edges:
                is_outgoing = (edge.source_node_id == curr_id)
                next_id = edge.target_node_id if is_outgoing else edge.source_node_id

                next_depth = curr_depth + 1
                next_conf = curr_conf * (edge.confidence or 1.0)
                next_path = curr_path + [edge.relationship_type]

                if next_id not in visited or next_depth < visited[next_id][0]:
                    visited[next_id] = (next_depth, next_conf, next_path)
                    queue.append((next_id, next_depth, next_conf, next_path))

        # Load all visited nodes except the root node
        target_ids = [nid for nid in visited.keys() if nid != node_id]
        if target_ids:
            nodes_query = self.db.query(KnowledgeGraphNode).filter(
                KnowledgeGraphNode.id.in_(target_ids),
                KnowledgeGraphNode.workspace_id == workspace_id,
                KnowledgeGraphNode.user_id == user_id
            )
            if node_types:
                nodes_query = nodes_query.filter(KnowledgeGraphNode.node_type.in_(node_types))

            for n in nodes_query.all():
                discovered_nodes[n.id] = n

        # Build scored items
        scored_items: List[RelatedEntityItem] = []
        for nid, node_obj in discovered_nodes.items():
            dist, conf, path = visited[nid]
            relevance = self.calculate_relevance_score(
                distance=dist,
                path_confidence=conf,
                rel_types=path,
                node_type=node_obj.node_type
            )
            scored_items.append(
                RelatedEntityItem(
                    node_id=node_obj.id,
                    node_type=node_obj.node_type,
                    name=node_obj.name,
                    description=node_obj.description,
                    distance=dist,
                    relevance_score=relevance,
                    relationship_path=path,
                    metadata=node_obj.meta_data
                )
            )

        # Deterministic sorting: highest relevance first, then shortest distance, then name, then UUID
        scored_items.sort(key=lambda item: (-item.relevance_score, item.distance, item.name, str(item.node_id)))
        final_items = scored_items[:max_limit]

        return RelatedEntitiesResponse(
            node_id=node_id,
            depth=max_depth,
            total_related=len(final_items),
            related_entities=final_items
        )

    # ---------------------------------------------------------
    # 3. Graph Context Generation (for RAG / Agents)
    # ---------------------------------------------------------

    def build_graph_context(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        entity_names: Optional[List[str]] = None,
        node_ids: Optional[List[uuid.UUID]] = None,
        depth: int = 2,
        max_entities: int = 20
    ) -> str:
        """
        Constructs safe, hierarchical textual graph context suitable for injection into LLM prompts.
        """
        start_nodes: List[KnowledgeGraphNode] = []

        # 1. Resolve starting nodes by IDs
        if node_ids:
            nodes_by_id = self.db.query(KnowledgeGraphNode).filter(
                KnowledgeGraphNode.id.in_(node_ids),
                KnowledgeGraphNode.workspace_id == workspace_id,
                KnowledgeGraphNode.user_id == user_id
            ).all()
            start_nodes.extend(nodes_by_id)

        # 2. Resolve starting nodes by Entity Names
        if entity_names:
            for name in entity_names:
                if not name or not name.strip():
                    continue
                clean_name = name.strip()
                matches = self.db.query(KnowledgeGraphNode).filter(
                    KnowledgeGraphNode.workspace_id == workspace_id,
                    KnowledgeGraphNode.user_id == user_id,
                    or_(
                        KnowledgeGraphNode.name.ilike(f"%{clean_name}%"),
                        KnowledgeGraphNode.external_id == clean_name
                    )
                ).limit(5).all()
                for m in matches:
                    if m.id not in [n.id for n in start_nodes]:
                        start_nodes.append(m)

        if not start_nodes:
            return ""

        # Bounded expansion
        start_nodes = start_nodes[:10]
        context_lines: List[str] = ["=== KNOWLEDGE GRAPH RELATIONSHIPS ==="]
        seen_edges: Set[Tuple[uuid.UUID, uuid.UUID, str]] = set()
        entities_included = 0

        for root in start_nodes:
            if entities_included >= max_entities:
                break

            context_lines.append(f"\nEntity: {root.name} [{root.node_type}]")
            if root.description:
                context_lines.append(f"  Description: {root.description[:200]}")

            # Expand neighbors
            related_resp = self.get_related_entities(
                user_id=user_id,
                workspace_id=workspace_id,
                node_id=root.id,
                depth=depth,
                limit=10
            )

            for rel in related_resp.related_entities:
                if entities_included >= max_entities:
                    break
                path_str = " -> ".join(rel.relationship_path) if rel.relationship_path else "CONNECTED_TO"
                context_lines.append(f"  ├── ({path_str}) -> {rel.name} [{rel.node_type}] (relevance: {rel.relevance_score})")
                entities_included += 1

        context_lines.append("=====================================")
        return "\n".join(context_lines)

    # ---------------------------------------------------------
    # 4. Shortest Path Discovery
    # ---------------------------------------------------------

    def find_shortest_path(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        max_depth: int = 5,
        allowed_relationship_types: Optional[List[str]] = None
    ) -> GraphPathResponse:
        """
        Finds the shortest directed/undirected path between two nodes in the workspace using BFS.
        """
        source_node = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=source_node_id)
        if not source_node:
            raise NodeNotFound(f"Source node {source_node_id} not found in workspace.")

        target_node = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=target_node_id)
        if not target_node:
            raise NodeNotFound(f"Target node {target_node_id} not found in workspace.")

        if source_node_id == target_node_id:
            return GraphPathResponse(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                path_found=True,
                distance=0,
                steps=[],
                nodes=[NodeResponse.model_validate(source_node)]
            )

        clamped_depth = max(1, min(max_depth, 10))

        # BFS queue element: (current_node_id, steps_taken, node_ids_in_path)
        queue: deque = deque([(source_node_id, [], [source_node_id])])
        visited: Set[uuid.UUID] = {source_node_id}

        while queue:
            curr_id, curr_steps, path_nodes = queue.popleft()

            if len(curr_steps) >= clamped_depth:
                continue

            # Fetch edges connected to curr_id
            edges_query = self.db.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.workspace_id == workspace_id,
                KnowledgeGraphEdge.user_id == user_id,
                or_(
                    KnowledgeGraphEdge.source_node_id == curr_id,
                    KnowledgeGraphEdge.target_node_id == curr_id
                )
            )
            if allowed_relationship_types:
                edges_query = edges_query.filter(KnowledgeGraphEdge.relationship_type.in_(allowed_relationship_types))

            edges = edges_query.all()

            for edge in edges:
                is_outgoing = (edge.source_node_id == curr_id)
                next_id = edge.target_node_id if is_outgoing else edge.source_node_id

                from_name = edge.source_node.name if is_outgoing else edge.target_node.name
                to_name = edge.target_node.name if is_outgoing else edge.source_node.name

                step = GraphPathStep(
                    from_node_id=edge.source_node_id if is_outgoing else edge.target_node_id,
                    from_node_name=from_name,
                    to_node_id=edge.target_node_id if is_outgoing else edge.source_node_id,
                    to_node_name=to_name,
                    relationship_type=edge.relationship_type,
                    direction="outgoing" if is_outgoing else "incoming",
                    confidence=edge.confidence or 1.0
                )

                if next_id == target_node_id:
                    # Path found!
                    full_steps = curr_steps + [step]
                    full_node_ids = path_nodes + [next_id]

                    # Retrieve all node objects in path
                    nodes_in_order = self.db.query(KnowledgeGraphNode).filter(
                        KnowledgeGraphNode.id.in_(full_node_ids),
                        KnowledgeGraphNode.workspace_id == workspace_id,
                        KnowledgeGraphNode.user_id == user_id
                    ).all()
                    nodes_dict = {n.id: n for n in nodes_in_order}
                    ordered_nodes = [
                        NodeResponse.model_validate(nodes_dict[nid])
                        for nid in full_node_ids if nid in nodes_dict
                    ]

                    return GraphPathResponse(
                        source_node_id=source_node_id,
                        target_node_id=target_node_id,
                        path_found=True,
                        distance=len(full_steps),
                        steps=full_steps,
                        nodes=ordered_nodes
                    )

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, curr_steps + [step], path_nodes + [next_id]))

        return GraphPathResponse(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            path_found=False,
            distance=-1,
            steps=[],
            nodes=[]
        )

    # ---------------------------------------------------------
    # 5. Relationship Analysis Between Two Entities
    # ---------------------------------------------------------

    def analyze_relationships(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        max_depth: int = 3
    ) -> RelationshipAnalysisResponse:
        """
        Performs in-depth relationship analysis between two nodes, identifying direct
        connections, shortest paths, and semantic summary.
        """
        source_node = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=source_node_id)
        if not source_node:
            raise NodeNotFound(f"Source node {source_node_id} not found in workspace.")

        target_node = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=target_node_id)
        if not target_node:
            raise NodeNotFound(f"Target node {target_node_id} not found in workspace.")

        direct_rels: List[RelationshipDetail] = []
        indirect_rels: List[RelationshipDetail] = []

        # 1. Direct Edges
        direct_edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            or_(
                and_(KnowledgeGraphEdge.source_node_id == source_node_id, KnowledgeGraphEdge.target_node_id == target_node_id),
                and_(KnowledgeGraphEdge.source_node_id == target_node_id, KnowledgeGraphEdge.target_node_id == source_node_id)
            )
        ).all()

        for edge in direct_edges:
            direction = "outgoing" if edge.source_node_id == source_node_id else "incoming"
            direct_rels.append(
                RelationshipDetail(
                    relationship_type=edge.relationship_type,
                    direction=direction,
                    confidence=edge.confidence or 1.0,
                    distance=1,
                    via_nodes=[]
                )
            )

        # 2. Indirect Path
        shortest_path = self.find_shortest_path(
            user_id=user_id,
            workspace_id=workspace_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            max_depth=max_depth
        )

        min_distance = None
        if direct_rels:
            min_distance = 1
        elif shortest_path.path_found:
            min_distance = shortest_path.distance
            via_names = [step.to_node_name for step in shortest_path.steps[:-1]]
            rel_summary = " -> ".join([step.relationship_type for step in shortest_path.steps])
            indirect_rels.append(
                RelationshipDetail(
                    relationship_type=rel_summary,
                    direction="outgoing",
                    confidence=min(step.confidence for step in shortest_path.steps) if shortest_path.steps else 1.0,
                    distance=shortest_path.distance,
                    via_nodes=via_names
                )
            )

        are_connected = bool(direct_rels or indirect_rels)

        # Build Summary
        if direct_rels:
            rel_names = ", ".join([f"{r.relationship_type} ({r.direction})" for r in direct_rels])
            summary = f"Directly connected: {source_node.name} and {target_node.name} via {rel_names}."
        elif indirect_rels:
            summary = f"Indirectly connected across {min_distance} hops via {', '.join(indirect_rels[0].via_nodes)}."
        else:
            summary = f"No direct or indirect path found between {source_node.name} and {target_node.name} within {max_depth} hops."

        return RelationshipAnalysisResponse(
            source_node=NodeResponse.model_validate(source_node),
            target_node=NodeResponse.model_validate(target_node),
            are_connected=are_connected,
            min_distance=min_distance,
            direct_relationships=direct_rels,
            indirect_relationships=indirect_rels,
            summary=summary
        )

    # ---------------------------------------------------------
    # 6. Enhanced Graph Search
    # ---------------------------------------------------------

    def enhanced_graph_search(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        query: Optional[str] = None,
        node_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        depth: int = 1,
        limit: int = 50
    ) -> List[RelatedEntityItem]:
        """
        Searches graph entities with optional neighbor expansion and deterministic relevance ranking.
        """
        nodes_q = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        )

        if query and query.strip():
            clean_q = query.strip()
            nodes_q = nodes_q.filter(
                or_(
                    KnowledgeGraphNode.name.ilike(f"%{clean_q}%"),
                    KnowledgeGraphNode.description.ilike(f"%{clean_q}%"),
                    KnowledgeGraphNode.external_id.ilike(f"%{clean_q}%")
                )
            )

        if node_type:
            nodes_q = nodes_q.filter(KnowledgeGraphNode.node_type == node_type)

        matched_roots = nodes_q.limit(limit).all()

        results: List[RelatedEntityItem] = []
        seen_ids: Set[uuid.UUID] = set()

        for root in matched_roots:
            if root.id not in seen_ids:
                seen_ids.add(root.id)
                results.append(
                    RelatedEntityItem(
                        node_id=root.id,
                        node_type=root.node_type,
                        name=root.name,
                        description=root.description,
                        distance=0,
                        relevance_score=1.0,
                        relationship_path=[],
                        metadata=root.meta_data
                    )
                )

            if depth > 0:
                rel_types = [relationship_type] if relationship_type else None
                related = self.get_related_entities(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    node_id=root.id,
                    depth=depth,
                    limit=10,
                    relationship_types=rel_types
                )
                for r in related.related_entities:
                    if r.node_id not in seen_ids:
                        seen_ids.add(r.node_id)
                        results.append(r)

        results.sort(key=lambda item: (-item.relevance_score, item.distance, item.name))
        return results[:limit]
