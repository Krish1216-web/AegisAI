import time
import uuid
import json
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import redis
from loguru import logger

from app.core.config import settings
from app.models.rag import RAGQuery
from app.schemas.rag import Citation, RAGResponse
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.knowledge_graph_intelligence import KnowledgeGraphIntelligenceService
from app.core.rag.base import (
    BaseRetriever,
    BaseReranker,
    BaseCitationSystem,
    BaseGenerationFlow
)
from app.core.rag.hybrid.models import (
    HybridRetrievedItem,
    HybridFusionConfig,
    HybridRAGResult
)
from app.core.rag.hybrid.query_analysis import QueryEntityExtractor
from app.core.rag.hybrid.fusion import HybridScoreFusion
from app.core.rag.hybrid.context import HybridContextBuilder

class HybridRAGService:
    """
    Production-grade Hybrid RAG Engine integrating vector similarity retrieval,
    knowledge graph intelligence, deterministic score fusion, and multi-agent reasoning.
    """
    def __init__(
        self,
        db: Session,
        redis_client: Optional[redis.Redis],
        retriever: BaseRetriever,
        reranker: BaseReranker,
        citation_system: BaseCitationSystem,
        generator: BaseGenerationFlow,
        config: Optional[HybridFusionConfig] = None
    ):
        self.db = db
        self.redis = redis_client
        self.retriever = retriever
        self.reranker = reranker
        self.citation_system = citation_system
        self.generator = generator
        self.config = config or HybridFusionConfig()
        self.fusion = HybridScoreFusion(self.config)
        self.context_builder = HybridContextBuilder(self.config)
        self.kg_service = KnowledgeGraphService(db)
        self.kg_intel = KnowledgeGraphIntelligenceService(db)

    def _get_cache_key(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        top_k: int,
        graph_depth: int
    ) -> str:
        payload = {
            "query": query,
            "top_k": top_k,
            "graph_depth": graph_depth
        }
        serialized = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"aegis:hybrid_rag_cache:{workspace_id}:{user_id}:{h}"

    async def query_hybrid(
        self,
        query: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        top_k: int = 5,
        graph_depth: int = 2,
        similarity_threshold: float = 0.0,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> HybridRAGResult:
        """
        Executes unified Hybrid Vector + Graph RAG retrieval, context fusion, and grounded answer synthesis.
        """
        start_time = time.perf_counter()
        active_provider = provider or settings.DEFAULT_AI_PROVIDER
        active_model = model or settings.DEFAULT_AI_MODEL

        # 1. Caching Check
        cache_key = self._get_cache_key(workspace_id, user_id, query, top_k, graph_depth)
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return HybridRAGResult.model_validate(data)
            except Exception as ce:
                logger.warning(f"Hybrid RAG cache read error: {ce}")

        # 2. Query Entity & Intent Analysis & Resolution
        intent = QueryEntityExtractor.analyze_query_intent(query)
        extracted_entity_names = intent.get("entities", [])
        
        # 3. Vector Retrieval & Reranking
        vector_candidates: List[Dict[str, Any]] = []
        try:
            raw_retrieved = await self.retriever.retrieve(
                db=self.db,
                query=query,
                user_id=user_id,
                workspace_id=workspace_id,
                limit=top_k * 2,
                similarity_threshold=similarity_threshold
            )
            if raw_retrieved:
                vector_candidates = self.reranker.rerank(query=query, candidates=raw_retrieved)
        except Exception as ve:
            logger.warning(f"Vector retrieval warning in Hybrid RAG: {ve}")

        # 4. Knowledge Graph Retrieval & Intelligence via Entity Resolution
        from app.services.entity_extraction.resolver import EntityResolver
        from app.services.entity_extraction.models import ExtractedEntity
        
        resolver = EntityResolver(self.db)
        resolved_nodes: List[KnowledgeGraphNode] = []
        matched_node_ids: List[uuid.UUID] = []
        graph_nodes: List[Dict[str, Any]] = []
        graph_edges_data: List[Dict[str, Any]] = []
        graph_context_str = ""

        try:
            # A. Resolve extracted entity mentions against tenant graph
            for ent_name in extracted_entity_names:
                mock_ent = ExtractedEntity(name=ent_name, entity_type="SKILL")
                node, res = resolver.resolve_entity(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    extracted=mock_ent,
                    allow_fuzzy=True
                )
                if node and node.id not in matched_node_ids:
                    matched_node_ids.append(node.id)
                    resolved_nodes.append(node)
                    graph_nodes.append({
                        "id": str(node.id),
                        "name": node.name,
                        "node_type": node.node_type,
                        "description": node.description,
                        "relevance_score": res.confidence,
                        "metadata": node.meta_data or {}
                    })

            # B. Search matching nodes for general query text
            found = self.kg_service.search_nodes(
                user_id=user_id,
                workspace_id=workspace_id,
                query=query,
                limit=5
            )
            for n in found:
                if n.id not in matched_node_ids:
                    matched_node_ids.append(n.id)
                    resolved_nodes.append(n)
                    graph_nodes.append({
                        "id": str(n.id),
                        "name": n.name,
                        "node_type": n.node_type,
                        "description": n.description,
                        "relevance_score": 0.85,
                        "metadata": n.meta_data or {}
                    })

            # C. Fetch active edges between matched nodes
            if matched_node_ids:
                edge_res = self.kg_service.list_edges(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    limit=50
                )
                all_edges = edge_res[0] if isinstance(edge_res, tuple) else edge_res
                id_set = set(matched_node_ids)
                for edge in all_edges:
                    if edge.source_node_id in id_set or edge.target_node_id in id_set:
                        graph_edges_data.append({
                            "id": str(edge.id),
                            "source_node_id": str(edge.source_node_id),
                            "target_node_id": str(edge.target_node_id),
                            "relationship_type": edge.relationship_type,
                            "confidence": edge.confidence,
                            "properties": edge.meta_data or {}
                        })

            # D. Build structured hierarchical graph context
            if matched_node_ids or extracted_entity_names:
                graph_context_str = self.kg_intel.build_graph_context(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    entity_names=extracted_entity_names if extracted_entity_names else None,
                    node_ids=matched_node_ids[:5] if matched_node_ids else None,
                    depth=graph_depth,
                    max_entities=15
                )
        except Exception as ge:
            logger.warning(f"Knowledge graph retrieval warning in Hybrid RAG: {ge}")

        # 5. Hybrid Score Fusion & Deduplication
        fused_items: List[HybridRetrievedItem] = self.fusion.fuse_results(
            vector_items=vector_candidates,
            graph_nodes=graph_nodes,
            graph_context_entities=extracted_entity_names
        )

        # 6. Conflict Detection
        has_conflict, conflict_summary = self.fusion.detect_conflicts(fused_items)

        # 7. Hybrid Context Construction
        combined_context = self.context_builder.build_hybrid_context(
            items=fused_items,
            graph_context=graph_context_str
        )

        # 8. Grounded Generation
        if not combined_context or not fused_items:
            answer = "I couldn't find sufficient document or knowledge graph evidence matching your query in this workspace."
            confidence = 0.1
        else:
            try:
                answer = await self.generator.generate(
                    query=query,
                    context=combined_context,
                    provider=active_provider,
                    model=active_model,
                    temperature=temperature
                )
                confidence = 0.95 if any(it.source_type == "hybrid" for it in fused_items) else 0.85
            except Exception as gen_err:
                logger.error(f"Generation error in Hybrid RAG: {gen_err}")
                answer = "An error occurred while synthesizing the answer from the retrieved evidence."
                confidence = 0.0

        # 9. Citation Extraction & Validation
        candidates_for_citations = [
            {"chunk": type("ChunkMock", (), {
                "id": it.chunk_id or uuid.uuid4(),
                "document_id": it.document_id or uuid.uuid4(),
                "page_number": it.page_number,
                "section_title": it.section_title,
                "document_name": it.document_name or "Document",
                "content": it.content
            })(), "score": it.score}
            for it in fused_items if it.chunk_id is not None
        ]

        citations: List[Citation] = []
        if candidates_for_citations:
            citations = self.citation_system.extract_citations(answer, candidates_for_citations)

        elapsed = time.perf_counter() - start_time

        result = HybridRAGResult(
            query=query,
            answer=answer,
            retrieved_chunks=fused_items,
            graph_entities=graph_nodes,
            graph_relationships=graph_edges_data,
            graph_context=graph_context_str,
            combined_context=combined_context,
            citations=citations,
            graph_citations=[{"node_id": str(it.node_id), "name": it.entity_name} for it in fused_items if it.node_id],
            confidence=round(confidence, 2),
            conflict_detected=has_conflict,
            conflict_summary=conflict_summary,
            retrieval_metrics={
                "latency_ms": round(elapsed * 1000, 2),
                "vector_candidates_count": len(vector_candidates),
                "graph_nodes_count": len(graph_nodes),
                "fused_items_count": len(fused_items),
                "has_conflict": has_conflict
            }
        )

        # Cache valid result in Redis
        if self.redis:
            try:
                self.redis.setex(cache_key, 3600, result.model_dump_json())
            except Exception as ce:
                logger.warning(f"Hybrid RAG cache write error: {ce}")

        return result
