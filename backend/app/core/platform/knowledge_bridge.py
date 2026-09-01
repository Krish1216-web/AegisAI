import uuid
import datetime
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger

from app.core.platform.context import PlatformContext
from app.core.platform.provenance import (
    ProvenanceItem,
    ProvenanceSourceType,
    ProvenanceTrustLevel
)
from app.core.mcp.security import CredentialStore
from app.core.platform.errors import InvalidExecutionInput

MAX_QUERY_LENGTH = 2000
MAX_TOP_K = 50
MAX_GRAPH_DEPTH = 5

class KnowledgeContextBridge:
    """
    Bidirectional context bridge between PlatformContext and RAG / Hybrid RAG / Knowledge Graph services.
    Enforces strict tenant isolation, immutable caller identity, bounded parameters, and unified provenance.
    """
    @staticmethod
    def validate_rag_query_params(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and bounds query input parameters without requiring a context."""
        query = input_data.get("query") or input_data.get("prompt") or input_data.get("text") or ""
        query_str = str(query).strip()
        if not query_str:
            raise InvalidExecutionInput("Query parameter 'query' cannot be empty.")
        if len(query_str) > MAX_QUERY_LENGTH:
            raise InvalidExecutionInput(f"Query length exceeds maximum limit of {MAX_QUERY_LENGTH} characters.")

        raw_limit = input_data.get("top_k", input_data.get("limit", 5))
        try:
            limit = max(1, min(int(raw_limit), MAX_TOP_K))
        except (ValueError, TypeError):
            limit = 5

        raw_thresh = input_data.get("similarity_threshold", 0.0)
        try:
            similarity_threshold = max(0.0, min(float(raw_thresh), 1.0))
        except (ValueError, TypeError):
            similarity_threshold = 0.0

        raw_depth = input_data.get("graph_depth", 2)
        try:
            graph_depth = max(1, min(int(raw_depth), MAX_GRAPH_DEPTH))
        except (ValueError, TypeError):
            graph_depth = 2

        sanitized = dict(input_data)
        sanitized["query"] = query_str
        sanitized["top_k"] = limit
        sanitized["limit"] = limit
        sanitized["similarity_threshold"] = similarity_threshold
        sanitized["graph_depth"] = graph_depth
        return sanitized

    @staticmethod
    def platform_context_to_rag_query(
        context: PlatformContext,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extracts, validates, and bounds RAG query parameters from input data.
        Guarantees tenant isolation: input_data cannot override workspace_id or user_id.
        """
        validated = KnowledgeContextBridge.validate_rag_query_params(input_data)

        return {
            "query": validated["query"],
            "workspace_id": context.workspace_id,
            "user_id": context.user_id,
            "limit": validated["limit"],
            "top_k": validated["top_k"],
            "similarity_threshold": validated["similarity_threshold"],
            "rerank": bool(input_data.get("rerank", True)),
            "include_graph": bool(input_data.get("include_graph", True)),
            "graph_depth": validated["graph_depth"],
            "metadata_filters": input_data.get("metadata_filters") or input_data.get("filters") or {},
            "provider": input_data.get("provider", "openai"),
            "model": input_data.get("model", "gpt-4o-mini")
        }

    @staticmethod
    def rag_response_to_execution_output(
        response_data: Any,
        context: PlatformContext
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Converts vector RAG retrieval response to platform execution output and ProvenanceItem list.
        """
        provenance_items: List[ProvenanceItem] = []

        if isinstance(response_data, dict):
            answer = response_data.get("answer") or response_data.get("context") or ""
            chunks = response_data.get("chunks") or response_data.get("results") or []
            citations = response_data.get("citations") or []
            metadata = response_data.get("metadata") or {}
        else:
            answer = getattr(response_data, "answer", getattr(response_data, "context", ""))
            chunks = getattr(response_data, "chunks", [])
            citations = getattr(response_data, "citations", [])
            metadata = getattr(response_data, "metadata", {})

        # Build provenance from chunks
        for idx, chunk in enumerate(chunks):
            if isinstance(chunk, dict):
                c_id = str(chunk.get("chunk_id") or chunk.get("id") or f"chunk_{idx}")
                doc_id = str(chunk.get("document_id") or "doc_unknown")
                text = str(chunk.get("text") or chunk.get("content") or "")
                score = float(chunk.get("score") or chunk.get("relevance_score") or 0.9)
                title = chunk.get("title") or chunk.get("document_title") or f"Document Chunk {doc_id[:8]}"
            else:
                c_id = str(getattr(chunk, "chunk_id", getattr(chunk, "id", f"chunk_{idx}")))
                doc_id = str(getattr(chunk, "document_id", "doc_unknown"))
                text = str(getattr(chunk, "text", getattr(chunk, "content", "")))
                score = float(getattr(chunk, "score", getattr(chunk, "relevance_score", 0.9)))
                title = getattr(chunk, "title", getattr(chunk, "document_title", f"Document Chunk {doc_id[:8]}"))

            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
                    source_id=c_id,
                    title=title,
                    snippet=text[:500] if text else None,
                    trust_level=ProvenanceTrustLevel.VERIFIED_RAG,
                    confidence=score,
                    workspace_id=context.workspace_id,
                    metadata={"document_id": doc_id, "chunk_id": c_id}
                )
            )

        output: Dict[str, Any] = {
            "answer": answer,
            "chunks_count": len(chunks),
            "results_count": len(chunks),
            "chunks": [c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else str(c)) for c in chunks],
            "citations": citations,
            "metadata": CredentialStore.redact_sensitive_dict(dict(metadata))
        }
        return output, provenance_items

    @staticmethod
    def hybrid_rag_response_to_execution_output(
        hybrid_result: Any,
        context: PlatformContext
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Converts Hybrid RAG (Vector + Graph) response to structured output and provenance.
        """
        provenance_items: List[ProvenanceItem] = []

        if isinstance(hybrid_result, dict):
            answer = hybrid_result.get("answer") or hybrid_result.get("fused_context") or ""
            doc_evidence = hybrid_result.get("document_evidence") or hybrid_result.get("chunks") or []
            graph_evidence = hybrid_result.get("graph_evidence") or hybrid_result.get("entities") or []
            relationships = hybrid_result.get("relationships") or []
            citations = hybrid_result.get("citations") or []
            confidence = float(hybrid_result.get("confidence") or 0.95)
        else:
            answer = getattr(hybrid_result, "answer", getattr(hybrid_result, "fused_context", ""))
            doc_evidence = getattr(hybrid_result, "document_evidence", getattr(hybrid_result, "chunks", []))
            graph_evidence = getattr(hybrid_result, "graph_evidence", getattr(hybrid_result, "entities", []))
            relationships = getattr(hybrid_result, "relationships", [])
            citations = getattr(hybrid_result, "citations", [])
            confidence = float(getattr(hybrid_result, "confidence", 0.95))

        # 1. Document Provenance
        for idx, doc in enumerate(doc_evidence):
            d_dict = doc if isinstance(doc, dict) else (doc.model_dump() if hasattr(doc, "model_dump") else {})
            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
                    source_id=str(d_dict.get("chunk_id") or f"chunk_{idx}"),
                    title=d_dict.get("title") or "Document Evidence",
                    snippet=str(d_dict.get("text") or d_dict.get("snippet", ""))[:500],
                    trust_level=ProvenanceTrustLevel.VERIFIED_RAG,
                    confidence=float(d_dict.get("score") or 0.9),
                    workspace_id=context.workspace_id,
                    metadata=d_dict
                )
            )

        # 2. Knowledge Graph Provenance
        for g in graph_evidence:
            g_dict = g if isinstance(g, dict) else (g.model_dump() if hasattr(g, "model_dump") else {})
            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.GRAPH_NODE,
                    source_id=str(g_dict.get("entity_id") or g_dict.get("id") or "kg_node"),
                    title=g_dict.get("name") or g_dict.get("title") or "Graph Entity",
                    snippet=str(g_dict.get("description", ""))[:500],
                    trust_level=ProvenanceTrustLevel.VERIFIED_GRAPH,
                    confidence=float(g_dict.get("confidence") or 0.95),
                    workspace_id=context.workspace_id,
                    metadata=g_dict
                )
            )

        output: Dict[str, Any] = {
            "answer": answer,
            "document_evidence": [d if isinstance(d, dict) else (d.model_dump() if hasattr(d, "model_dump") else str(d)) for d in doc_evidence],
            "graph_evidence": [g if isinstance(g, dict) else (g.model_dump() if hasattr(g, "model_dump") else str(g)) for g in graph_evidence],
            "relationships": [r if isinstance(r, dict) else (r.model_dump() if hasattr(r, "model_dump") else str(r)) for r in relationships],
            "citations": citations,
            "confidence_score": confidence
        }
        return output, provenance_items

    @staticmethod
    def graph_response_to_execution_output(
        graph_data: Any,
        context: PlatformContext
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Converts Knowledge Graph analysis results into platform execution output and provenance.
        """
        provenance_items: List[ProvenanceItem] = []

        if isinstance(graph_data, dict):
            nodes = graph_data.get("nodes") or graph_data.get("entities") or []
            edges = graph_data.get("edges") or graph_data.get("relationships") or []
            paths = graph_data.get("paths") or []
            summary = graph_data.get("summary") or "Graph analysis completed."
        else:
            nodes = getattr(graph_data, "nodes", getattr(graph_data, "entities", []))
            edges = getattr(graph_data, "edges", getattr(graph_data, "relationships", []))
            paths = getattr(graph_data, "paths", [])
            summary = getattr(graph_data, "summary", "Graph analysis completed.")

        for n in nodes:
            n_dict = n if isinstance(n, dict) else (n.model_dump() if hasattr(n, "model_dump") else {})
            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.GRAPH_NODE,
                    source_id=str(n_dict.get("id") or n_dict.get("node_id") or "kg_node"),
                    title=n_dict.get("name") or n_dict.get("label") or "KG Entity",
                    snippet=n_dict.get("description"),
                    trust_level=ProvenanceTrustLevel.VERIFIED_GRAPH,
                    confidence=float(n_dict.get("confidence") or 0.95),
                    workspace_id=context.workspace_id,
                    metadata=n_dict
                )
            )

        output: Dict[str, Any] = {
            "summary": summary,
            "nodes_count": len(nodes),
            "nodes_found": len(nodes),
            "edges_count": len(edges),
            "nodes": [n if isinstance(n, dict) else (n.model_dump() if hasattr(n, "model_dump") else str(n)) for n in nodes],
            "edges": [e if isinstance(e, dict) else (e.model_dump() if hasattr(e, "model_dump") else str(e)) for e in edges],
            "paths": paths
        }
        return output, provenance_items
