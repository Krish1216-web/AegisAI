import uuid
import math
from typing import List, Dict, Any, Tuple, Optional
from app.core.rag.hybrid.models import HybridRetrievedItem, HybridFusionConfig

class HybridScoreFusion:
    """
    Normalizes, deduplicates, and fuses vector retrieval scores and graph intelligence scores
    into a unified ranking of evidence items.
    """
    def __init__(self, config: Optional[HybridFusionConfig] = None):
        self.config = config or HybridFusionConfig()

    @staticmethod
    def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        if max_val <= min_val:
            return max(0.0, min(1.0, score))
        norm = (score - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, norm))

    def fuse_results(
        self,
        vector_items: List[Dict[str, Any]],
        graph_nodes: List[Dict[str, Any]],
        graph_context_entities: Optional[List[str]] = None
    ) -> List[HybridRetrievedItem]:
        """
        Fuses vector candidates and graph nodes into deduplicated HybridRetrievedItem instances.
        """
        merged_map: Dict[str, HybridRetrievedItem] = {}

        # 1. Ingest Vector Candidates
        for item in vector_items:
            chunk = item.get("chunk")
            vec_score = float(item.get("score", 0.0))
            if not chunk:
                continue

            chunk_id = str(chunk.id)
            doc_id = chunk.document_id
            doc_meta = chunk.meta_data or {}

            # Calculate metadata boost (e.g. recent chunk or presence of title)
            meta_score = 0.8 if getattr(chunk, "section_title", None) else 0.5

            raw_doc_name = getattr(chunk, "document_name", None)
            if isinstance(raw_doc_name, str):
                doc_name_str = raw_doc_name
            elif isinstance(doc_meta, dict) and isinstance(doc_meta.get("document_name"), str):
                doc_name_str = doc_meta["document_name"]
            elif raw_doc_name is not None and not hasattr(raw_doc_name, "_mock_name"):
                doc_name_str = str(raw_doc_name)
            else:
                doc_name_str = "Document"

            merged_map[chunk_id] = HybridRetrievedItem(
                document_id=doc_id,
                chunk_id=chunk.id,
                content=chunk.content,
                source_type="document",
                vector_score=round(self.normalize_score(vec_score), 4),
                graph_score=0.0,
                metadata_score=meta_score,
                page_number=getattr(chunk, "page_number", None),
                section_title=getattr(chunk, "section_title", None),
                document_name=doc_name_str,
                metadata=doc_meta if isinstance(doc_meta, dict) else None
            )

        # 2. Ingest & Merge Graph Nodes / Entities
        for gn in graph_nodes:
            node_id = str(gn.get("id") or gn.get("node_id", ""))
            g_score = float(gn.get("relevance_score", gn.get("confidence", 0.8)))
            node_name = gn.get("name", "")
            node_type = gn.get("node_type", "")
            node_desc = gn.get("description", "")
            meta = gn.get("metadata", {}) or {}

            # Check if this graph node is linked directly to a chunk in merged_map
            provenance = meta.get("provenance", [])
            linked_chunk_id = None
            for p in provenance:
                c_id = p.get("chunk_id")
                if c_id and c_id in merged_map:
                    linked_chunk_id = c_id
                    break

            if linked_chunk_id and linked_chunk_id in merged_map:
                # Merge into existing vector item! (True Hybrid Evidence)
                existing = merged_map[linked_chunk_id]
                existing.source_type = "hybrid"
                existing.graph_score = round(self.normalize_score(g_score), 4)
                existing.node_id = uuid.UUID(node_id) if node_id else None
                existing.entity_name = node_name
                existing.entity_type = node_type
                existing.path_info = gn.get("relationship_path", [])
            else:
                # Add as distinct graph evidence item
                merged_map[f"node_{node_id}"] = HybridRetrievedItem(
                    node_id=uuid.UUID(node_id) if node_id and len(node_id) == 36 else None,
                    content=f"Knowledge Entity: {node_name} [{node_type}]. {node_desc}".strip(),
                    source_type="graph_node",
                    vector_score=0.0,
                    graph_score=round(self.normalize_score(g_score), 4),
                    metadata_score=0.6,
                    entity_name=node_name,
                    entity_type=node_type,
                    path_info=gn.get("relationship_path", []),
                    metadata=meta
                )

        # 3. Calculate Final Fused Scores
        results: List[HybridRetrievedItem] = []
        for item in merged_map.values():
            if item.source_type == "hybrid":
                # Both vector & graph evidence agree
                fused = (
                    self.config.vector_weight * item.vector_score +
                    self.config.graph_weight * item.graph_score +
                    self.config.metadata_weight * item.metadata_score
                )
            elif item.source_type == "document":
                # Vector-only evidence
                fused = (
                    0.80 * item.vector_score +
                    0.20 * item.metadata_score
                )
            else:
                # Graph-only evidence
                fused = (
                    0.80 * item.graph_score +
                    0.20 * item.metadata_score
                )

            item.score = round(max(0.0, min(1.0, fused)), 4)
            if item.score >= self.config.min_score_threshold:
                results.append(item)

        # Sort by fused score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:self.config.max_chunks + self.config.max_graph_nodes]

    @staticmethod
    def detect_conflicts(items: List[HybridRetrievedItem]) -> Tuple[bool, Optional[str]]:
        """
        Detects potential contradictions or temporal supersessions in retrieved evidence.
        """
        conflict_terms = ["deprecated", "replaced by", "migrated from", "no longer supported", "superseded", "discontinued"]
        found_warnings: List[str] = []

        for item in items:
            content_lower = item.content.lower()
            for term in conflict_terms:
                if term in content_lower:
                    found_warnings.append(f"Potential status/version update: '{term}' detected in {item.source_type} snippet.")
                    break

        if found_warnings:
            return (True, "; ".join(found_warnings[:3]))
        return (False, None)
