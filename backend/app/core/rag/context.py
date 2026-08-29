from typing import List, Dict, Any
from app.core.rag.base import BaseContextBuilder

class ContextBuilder(BaseContextBuilder):
    def build_context(
        self,
        candidates: List[Dict[str, Any]],
        max_tokens: int = 4000
    ) -> str:
        if not candidates:
            return ""

        context_blocks = []
        accumulated_tokens = 0

        for idx, item in enumerate(candidates):
            chunk = item["chunk"]
            
            # Estimate chunk tokens using saved token_count, fallback to char-based estimation (1 token ~ 4 chars)
            chunk_tokens = getattr(chunk, "token_count", None)
            if chunk_tokens is None:
                chunk_tokens = max(len(chunk.content) // 4, 1)
            
            # Check limit
            if accumulated_tokens + chunk_tokens > max_tokens:
                # Do not add chunk if it overflows maximum tokens
                if len(context_blocks) > 0:
                    break

            # Resolve document file name
            doc_name = "Unknown Source"
            if hasattr(chunk, "document") and chunk.document:
                doc_name = chunk.document.original_filename or chunk.document.filename

            page_info = f", Page: {chunk.page_number}" if chunk.page_number else ""
            section_info = f", Section: {chunk.section_title}" if chunk.section_title else ""
            offset_info = f", Offset: {chunk.start_offset}-{chunk.end_offset}" if chunk.start_offset is not None else ""
            
            header = f"[Source {idx + 1}: {doc_name}{page_info}{section_info}{offset_info}]"
            block = f"{header}\n{chunk.content}"
            
            context_blocks.append(block)
            accumulated_tokens += chunk_tokens

        return "\n\n".join(context_blocks)
