import uuid
import time
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.knowledge_graph_intelligence import KnowledgeGraphIntelligenceService
from app.services.entity_extraction.resolver import EntityResolver
from app.services.entity_extraction.models import ExtractedEntity
from app.core.rag.hybrid.query_analysis import QueryEntityExtractor

class GraphReasoningAgent(BaseAgent):
    """
    Autonomous Knowledge Graph Reasoning Agent responsible for topological extraction,
    multi-hop pathfinding, dependency analysis, and structured graph citation generation.
    """
    def __init__(self, ai_service: Any, db: Optional[Any] = None):
        super().__init__()
        self.ai_service = ai_service
        self.db = db

    @property
    def name(self) -> str:
        return "GraphReasoningAgent"

    @property
    def description(self) -> str:
        return "Performs entity graph resolution, topological exploration, and path reasoning."

    def validate_input(self, state: AgentState) -> bool:
        return bool(state.get("original_prompt") or state.get("messages"))

    def validate_output(self, result: AgentResult) -> bool:
        return bool(result.output)

    def health_check(self) -> bool:
        return True

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        start_time = time.perf_counter()
        query = state.get("original_prompt") or context.configuration.get("prompt") or ""
        if not query and state.get("messages"):
            query = state["messages"][-1]["content"]

        user_id_str = state.get("user_id") or context.user_id
        workspace_id_str = state.get("workspace_id") or context.workspace_id

        if not user_id_str or not workspace_id_str:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                output=json.dumps({"error": "Missing required user_id or workspace_id"}),
                confidence=0.0,
                execution_time=time.perf_counter() - start_time,
                token_usage={},
                errors="Missing required user_id or workspace_id for tenant graph reasoning."
            )

        try:
            user_id = uuid.UUID(str(user_id_str))
            workspace_id = uuid.UUID(str(workspace_id_str))
        except ValueError as ve:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                output=json.dumps({"error": str(ve)}),
                confidence=0.0,
                execution_time=time.perf_counter() - start_time,
                token_usage={},
                errors=f"Invalid UUID format: {ve}"
            )

        db = context.configuration.get("db") if getattr(context, "configuration", None) else None
        if not db:
            db = self.db

        if not db:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                output=json.dumps({"error": "Database session unavailable"}),
                confidence=0.0,
                execution_time=time.perf_counter() - start_time,
                token_usage={},
                errors="Database session unavailable for GraphReasoningAgent."
            )

        kg_service = KnowledgeGraphService(db)
        kg_intel = KnowledgeGraphIntelligenceService(db)
        resolver = EntityResolver(db)

        # 1. Extract entities and query intent
        intent = QueryEntityExtractor.analyze_query_intent(query)
        extracted_entity_names = intent.get("entities", [])

        # 2. Resolve entities against tenant graph
        matched_node_ids: List[uuid.UUID] = []
        matched_nodes: List[KnowledgeGraphNode] = []
        node_summaries: List[Dict[str, Any]] = []

        for ent_name in extracted_entity_names:
            mock_ent = ExtractedEntity(name=ent_name, entity_type="PROJECT")
            node, res = resolver.resolve_entity(
                user_id=user_id,
                workspace_id=workspace_id,
                extracted=mock_ent,
                allow_fuzzy=True
            )
            if node and node.id not in matched_node_ids:
                matched_node_ids.append(node.id)
                matched_nodes.append(node)
                node_summaries.append({
                    "id": str(node.id),
                    "name": node.name,
                    "node_type": node.node_type,
                    "description": node.description,
                    "confidence": res.confidence,
                    "metadata": node.meta_data or {}
                })

        # Match workspace nodes directly mentioned in the query
        query_lower = query.lower()
        ws_nodes_res = kg_service.list_nodes(user_id=user_id, workspace_id=workspace_id, limit=200)
        ws_nodes = ws_nodes_res[0] if isinstance(ws_nodes_res, tuple) else ws_nodes_res
        for n in ws_nodes:
            if n.name.lower() in query_lower and n.id not in matched_node_ids:
                matched_node_ids.append(n.id)
                matched_nodes.append(n)
                node_summaries.append({
                    "id": str(n.id),
                    "name": n.name,
                    "node_type": n.node_type,
                    "description": n.description,
                    "confidence": 0.95,
                    "metadata": n.meta_data or {}
                })

        # 3. Fetch connected edges
        edges_data: List[Dict[str, Any]] = []
        edge_res = kg_service.list_edges(user_id=user_id, workspace_id=workspace_id, limit=50)
        all_edges = edge_res[0] if isinstance(edge_res, tuple) else edge_res
        id_set = set(matched_node_ids)

        for edge in all_edges:
            if edge.source_node_id in id_set or edge.target_node_id in id_set:
                edges_data.append({
                    "id": str(edge.id),
                    "source_node_id": str(edge.source_node_id),
                    "target_node_id": str(edge.target_node_id),
                    "relationship_type": edge.relationship_type,
                    "confidence": edge.confidence,
                    "properties": edge.meta_data or {}
                })

        # 4. Shortest path finding if >= 2 entities matched
        paths_data: List[Dict[str, Any]] = []
        if len(matched_node_ids) >= 2:
            path_res = kg_intel.find_shortest_path(
                user_id=user_id,
                workspace_id=workspace_id,
                source_node_id=matched_node_ids[0],
                target_node_id=matched_node_ids[1],
                max_depth=4
            )
            is_found = getattr(path_res, "path_found", False) if hasattr(path_res, "path_found") else (isinstance(path_res, dict) and path_res.get("path_found"))
            if is_found:
                path_dict = path_res.model_dump() if hasattr(path_res, "model_dump") else (path_res if isinstance(path_res, dict) else {})
                paths_data.append(path_dict)

        # 5. Build structured graph context
        graph_context_str = kg_intel.build_graph_context(
            user_id=user_id,
            workspace_id=workspace_id,
            entity_names=extracted_entity_names if extracted_entity_names else None,
            node_ids=matched_node_ids[:5] if matched_node_ids else None,
            depth=2,
            max_entities=15
        )

        # 6. Generate authentic graph citations
        graph_citations: List[Dict[str, Any]] = []
        for n in matched_nodes:
            graph_citations.append({
                "source_type": "graph",
                "node_id": str(n.id),
                "node_name": n.name,
                "node_type": n.node_type,
                "confidence": 0.95
            })

        for e in edges_data[:5]:
            graph_citations.append({
                "source_type": "graph_edge",
                "edge_id": e["id"],
                "source_node_id": e["source_node_id"],
                "target_node_id": e["target_node_id"],
                "relationship_type": e["relationship_type"],
                "confidence": e["confidence"]
            })

        confidence = 0.90 if matched_node_ids else 0.20
        elapsed = time.perf_counter() - start_time

        result_payload = {
            "query": query,
            "entities": extracted_entity_names,
            "matched_nodes_count": len(matched_nodes),
            "matched_edges_count": len(edges_data),
            "paths_found": len(paths_data),
            "graph_context": graph_context_str,
            "citations": graph_citations,
            "confidence": confidence,
            "latency_ms": round(elapsed * 1000, 2)
        }

        # Update AgentState
        state["graph_query"] = query
        state["graph_reasoning_required"] = True if matched_node_ids else False
        state["graph_entities"] = extracted_entity_names
        state["graph_nodes"] = node_summaries
        state["graph_edges"] = edges_data
        state["graph_paths"] = paths_data
        state["graph_context"] = graph_context_str
        state["graph_confidence"] = confidence
        state["graph_citations"] = graph_citations
        state["graph_reasoning_result"] = result_payload
        state["execution_status"] = ExecutionStatus.GRAPH_REASONING

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output=json.dumps(result_payload),
            confidence=confidence,
            execution_time=elapsed,
            token_usage={"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
            metadata=result_payload
        )
