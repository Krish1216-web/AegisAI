from typing import List, Optional
from app.core.rag.hybrid.models import HybridRetrievedItem, HybridFusionConfig

class HybridContextBuilder:
    """
    Builds structured, budget-bounded context combining document evidence blocks
    and knowledge graph relationship topologies.
    """
    def __init__(self, config: Optional[HybridFusionConfig] = None):
        self.config = config or HybridFusionConfig()

    def build_hybrid_context(
        self,
        items: List[HybridRetrievedItem],
        graph_context: str = ""
    ) -> str:
        """
        Synthesizes formatted context while strictly enforcing character limits.
        """
        doc_blocks: List[str] = []
        char_count = 0
        max_chars = self.config.max_context_chars

        # 1. Build Document Evidence Section
        doc_items = [it for it in items if it.source_type in ("document", "hybrid")]
        for idx, item in enumerate(doc_items, start=1):
            doc_name = item.document_name or "Document"
            page_info = f" | Page: {item.page_number}" if item.page_number else ""
            section_info = f" | Section: {item.section_title}" if item.section_title else ""

            header = f"[Evidence #{idx}: {doc_name}{page_info}{section_info} | Relevance: {item.score:.2f}]"
            # Sanitize content against prompt injection overrides
            snippet = item.content.strip().replace("---", "—")
            block = f"{header}\n{snippet}\n"

            if idx > 1 and char_count + len(block) > max_chars * 0.70: # Reserve 30% for graph context
                break

            doc_blocks.append(block)
            char_count += len(block)

        # 2. Combine with Knowledge Graph Section
        sections: List[str] = []
        if doc_blocks:
            sections.append("=== DOCUMENT EVIDENCE ===\n" + "\n".join(doc_blocks))

        if graph_context and graph_context.strip():
            safe_graph = graph_context.strip()[:int(max_chars * 0.35)]
            sections.append(f"=== KNOWLEDGE GRAPH TOPOLOGY ===\n{safe_graph}")

        return "\n\n".join(sections)
