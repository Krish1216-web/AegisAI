import uuid
import time
import difflib
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.schemas.knowledge_graph import (
    GraphAnalyticsOverview,
    GraphHealthReport,
    TopConnectedEntity,
    DuplicateCandidate,
    SearchResultItem,
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    NodeResponse
)
from app.services.entity_extraction.normalizer import EntityNormalizer

class GraphAnalyticsService:
    """
    Production-grade Knowledge Graph Search & Analytics layer enforcing
    strict multi-tenancy, deterministic ranking, health diagnostics, and connectivity metrics.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_analytics_overview(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> GraphAnalyticsOverview:
        """
        Computes comprehensive structural and provenance statistics for the tenant graph.
        """
        # 1. Node counts by type
        node_type_counts: Dict[str, int] = {}
        nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).all()

        total_nodes = len(nodes)
        prov_dist: Dict[str, int] = {"document": 0, "memory": 0, "system": 0, "other": 0}

        for n in nodes:
            node_type_counts[n.node_type] = node_type_counts.get(n.node_type, 0) + 1
            meta = n.meta_data or {}
            prov_list = meta.get("provenance", [])
            if prov_list:
                for p in prov_list:
                    st = p.get("source_type", "document").lower()
                    if "doc" in st:
                        prov_dist["document"] += 1
                    elif "mem" in st:
                        prov_dist["memory"] += 1
                    else:
                        prov_dist["other"] += 1
            elif meta.get("system_anchor"):
                prov_dist["system"] += 1
            else:
                prov_dist["other"] += 1

        # 2. Edge counts by relationship type & confidence
        edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id
        ).all()

        total_edges = len(edges)
        edge_type_counts: Dict[str, int] = {}
        total_conf = 0.0

        # Degree calculations
        in_degree_map: Dict[uuid.UUID, int] = {}
        out_degree_map: Dict[uuid.UUID, int] = {}

        for e in edges:
            edge_type_counts[e.relationship_type] = edge_type_counts.get(e.relationship_type, 0) + 1
            total_conf += (e.confidence or 1.0)
            out_degree_map[e.source_node_id] = out_degree_map.get(e.source_node_id, 0) + 1
            in_degree_map[e.target_node_id] = in_degree_map.get(e.target_node_id, 0) + 1

        avg_conf = round(total_conf / total_edges, 3) if total_edges > 0 else 0.0

        # 3. Connectivity metrics
        isolated_count = 0
        max_deg = 0
        total_degrees = 0

        for n in nodes:
            deg = in_degree_map.get(n.id, 0) + out_degree_map.get(n.id, 0)
            total_degrees += deg
            if deg > max_deg:
                max_deg = deg
            if deg == 0:
                isolated_count += 1

        connected_count = total_nodes - isolated_count
        avg_deg = round(total_degrees / total_nodes, 2) if total_nodes > 0 else 0.0

        # Density: |E| / (|V| * (|V| - 1)) for directed graph
        density = 0.0
        if total_nodes > 1:
            density = round(total_edges / (total_nodes * (total_nodes - 1)), 4)

        return GraphAnalyticsOverview(
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_by_type=node_type_counts,
            edges_by_type=edge_type_counts,
            average_degree=avg_deg,
            max_degree=max_deg,
            isolated_nodes_count=isolated_count,
            connected_nodes_count=connected_count,
            graph_density=density,
            average_confidence=avg_conf,
            provenance_distribution=prov_dist
        )

    def get_graph_health(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> GraphHealthReport:
        """
        Evaluates structural integrity, orphan rate, confidence distributions, and conflicts.
        """
        overview = self.get_analytics_overview(user_id, workspace_id)
        orphan_rate = round(overview.isolated_nodes_count / overview.total_nodes, 3) if overview.total_nodes > 0 else 0.0

        edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id
        ).all()

        low_conf_count = sum(1 for e in edges if e.confidence < 0.60)
        conflicts_count = 0
        for e in edges:
            meta = e.meta_data or {}
            conflicts = meta.get("conflict_indicators", [])
            if conflicts:
                conflicts_count += len(conflicts)

        nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).all()
        unresolved_prov = sum(1 for n in nodes if not (n.meta_data or {}).get("provenance") and not (n.meta_data or {}).get("system_anchor"))

        # Health Classification
        diagnostics: List[str] = []
        if orphan_rate > 0.50 and overview.total_nodes > 10:
            status = "CRITICAL"
            diagnostics.append(f"High percentage ({int(orphan_rate * 100)}%) of isolated entities with no connected relationships.")
        elif orphan_rate > 0.25 or low_conf_count > 5 or conflicts_count > 0:
            status = "WARNING"
            if orphan_rate > 0.25:
                diagnostics.append(f"{int(orphan_rate * 100)}% of entities are isolated.")
            if low_conf_count > 0:
                diagnostics.append(f"{low_conf_count} relationships have low confidence (< 0.60).")
            if conflicts_count > 0:
                diagnostics.append(f"{conflicts_count} semantic contradiction indicators detected.")
        else:
            status = "HEALTHY"
            diagnostics.append("Graph topology is well-connected with high average relationship confidence.")

        if unresolved_prov > 0:
            diagnostics.append(f"{unresolved_prov} nodes lack explicit document or memory provenance.")

        return GraphHealthReport(
            status=status,
            orphan_rate=orphan_rate,
            low_confidence_edges_count=low_conf_count,
            conflicts_count=conflicts_count,
            unresolved_provenance_count=unresolved_prov,
            diagnostic_messages=diagnostics
        )

    def get_top_connected_entities(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 10
    ) -> List[TopConnectedEntity]:
        """
        Returns highest-degree hub nodes in the graph.
        """
        nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).all()

        edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id
        ).all()

        in_degree: Dict[uuid.UUID, int] = {}
        out_degree: Dict[uuid.UUID, int] = {}
        for e in edges:
            out_degree[e.source_node_id] = out_degree.get(e.source_node_id, 0) + 1
            in_degree[e.target_node_id] = in_degree.get(e.target_node_id, 0) + 1

        scored: List[TopConnectedEntity] = []
        for n in nodes:
            ind = in_degree.get(n.id, 0)
            outd = out_degree.get(n.id, 0)
            scored.append(TopConnectedEntity(
                node_id=n.id,
                name=n.name,
                node_type=n.node_type,
                degree=ind + outd,
                in_degree=ind,
                out_degree=outd
            ))

        scored.sort(key=lambda x: x.degree, reverse=True)
        return scored[:limit]

    def get_orphan_nodes(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50
    ) -> List[NodeResponse]:
        """
        Returns entities with zero incoming and zero outgoing relationships.
        """
        nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).all()

        edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id
        ).all()

        connected_ids = set()
        for e in edges:
            connected_ids.add(e.source_node_id)
            connected_ids.add(e.target_node_id)

        orphans = [NodeResponse.model_validate(n) for n in nodes if n.id not in connected_ids]
        return orphans[:limit]

    def detect_duplicate_candidates(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        similarity_threshold: float = 0.85,
        limit: int = 20
    ) -> List[DuplicateCandidate]:
        """
        Identifies potential duplicate entity pairs of identical node type for non-destructive review.
        """
        nodes = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        ).all()

        # Group by node type
        by_type: Dict[str, List[KnowledgeGraphNode]] = {}
        for n in nodes:
            by_type.setdefault(n.node_type, []).append(n)

        candidates: List[DuplicateCandidate] = []

        for ntype, type_nodes in by_type.items():
            for i in range(len(type_nodes)):
                for j in range(i + 1, len(type_nodes)):
                    n1 = type_nodes[i]
                    n2 = type_nodes[j]
                    norm1 = EntityNormalizer.get_lookup_key(n1.name)
                    norm2 = EntityNormalizer.get_lookup_key(n2.name)

                    if norm1 == norm2:
                        candidates.append(DuplicateCandidate(
                            source_node_id=n1.id,
                            source_name=n1.name,
                            target_node_id=n2.id,
                            target_name=n2.name,
                            entity_type=ntype,
                            similarity_score=0.98,
                            reason=f"Normalized key match: '{norm1}'"
                        ))
                    else:
                        ratio = difflib.SequenceMatcher(None, n1.name.lower(), n2.name.lower()).ratio()
                        if ratio >= similarity_threshold:
                            candidates.append(DuplicateCandidate(
                                source_node_id=n1.id,
                                source_name=n1.name,
                                target_node_id=n2.id,
                                target_name=n2.name,
                                entity_type=ntype,
                                similarity_score=round(ratio, 2),
                                reason=f"Fuzzy string similarity ({int(ratio * 100)}%)"
                            ))

        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        return candidates[:limit]

    def advanced_search(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: AdvancedSearchRequest
    ) -> AdvancedSearchResponse:
        """
        Performs multi-criterion search with deterministic explainable relevance ranking.
        """
        start_time = time.perf_counter()
        query_str = (req.query or "").strip().lower()

        # 1. Base query with tenant isolation
        q = self.db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.workspace_id == workspace_id,
            KnowledgeGraphNode.user_id == user_id
        )

        if req.node_type and req.node_type != "ALL":
            q = q.filter(KnowledgeGraphNode.node_type == req.node_type)

        nodes = q.all()

        # Degree index
        edges = self.db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.workspace_id == workspace_id,
            KnowledgeGraphEdge.user_id == user_id,
            KnowledgeGraphEdge.confidence >= req.min_confidence
        ).all()

        degree_map: Dict[uuid.UUID, int] = {}
        for e in edges:
            degree_map[e.source_node_id] = degree_map.get(e.source_node_id, 0) + 1
            degree_map[e.target_node_id] = degree_map.get(e.target_node_id, 0) + 1

        scored_items: List[SearchResultItem] = []

        for n in nodes:
            name_lower = n.name.lower()
            desc_lower = (n.description or "").lower()
            deg = degree_map.get(n.id, 0)
            conn_boost = min(0.15, deg * 0.015)

            if not query_str:
                # Unfiltered scan: score primarily on connectivity
                score = round(0.5 + conn_boost, 3)
                scored_items.append(SearchResultItem(
                    node=NodeResponse.model_validate(n),
                    relevance_score=score,
                    match_type="partial",
                    degree=deg
                ))
                continue

            # Deterministic matching hierarchy
            if name_lower == query_str:
                score = round(1.0 + conn_boost, 3)
                scored_items.append(SearchResultItem(
                    node=NodeResponse.model_validate(n),
                    relevance_score=score,
                    match_type="exact",
                    degree=deg
                ))
            elif name_lower.startswith(query_str):
                score = round(0.85 + conn_boost, 3)
                scored_items.append(SearchResultItem(
                    node=NodeResponse.model_validate(n),
                    relevance_score=score,
                    match_type="prefix",
                    degree=deg
                ))
            elif query_str in name_lower:
                score = round(0.70 + conn_boost, 3)
                scored_items.append(SearchResultItem(
                    node=NodeResponse.model_validate(n),
                    relevance_score=score,
                    match_type="partial",
                    degree=deg
                ))
            elif query_str in desc_lower:
                score = round(0.50 + conn_boost, 3)
                scored_items.append(SearchResultItem(
                    node=NodeResponse.model_validate(n),
                    relevance_score=score,
                    match_type="description",
                    degree=deg
                ))
            else:
                ratio = difflib.SequenceMatcher(None, query_str, name_lower).ratio()
                if ratio >= 0.70:
                    score = round(ratio * 0.6 + conn_boost, 3)
                    scored_items.append(SearchResultItem(
                        node=NodeResponse.model_validate(n),
                        relevance_score=score,
                        match_type="fuzzy",
                        degree=deg
                    ))

        scored_items.sort(key=lambda x: x.relevance_score, reverse=True)
        total_matched = len(scored_items)
        paginated = scored_items[req.offset : req.offset + req.limit]
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return AdvancedSearchResponse(
            results=paginated,
            total_matched=total_matched,
            search_latency_ms=elapsed_ms
        )
