import re
from typing import List, Dict, Any, Optional
from app.core.rag.base import BaseReranker

class SimpleScoreReranker(BaseReranker):
    def __init__(self, w_sim: float = 0.7, w_keyword: float = 0.3):
        self.w_sim = w_sim
        self.w_keyword = w_keyword

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # Tokenize query into lowercase words of length >= 2
        query_words = set(re.findall(r'\b\w{2,}\b', query.lower()))
        
        reranked = []
        for item in candidates:
            chunk = item["chunk"]
            similarity = item["score"]
            
            # Compute keyword overlap score
            chunk_content = chunk.content.lower()
            chunk_words = set(re.findall(r'\b\w{2,}\b', chunk_content))
            
            if not query_words:
                keyword_score = 0.0
            else:
                overlap = query_words.intersection(chunk_words)
                keyword_score = len(overlap) / len(query_words)
                
            # Base combined score
            score = (self.w_sim * similarity) + (self.w_keyword * keyword_score)
            
            # Metadata boost checks
            boost = 0.0
            if metadata_filters:
                # 1. File extension match boost
                ext_filter = metadata_filters.get("file_extension")
                if ext_filter and hasattr(chunk, "document") and chunk.document:
                    if chunk.document.file_extension.lower() == ext_filter.lower():
                        boost += 0.05
                
                # 2. Section title match boost
                sec_filter = metadata_filters.get("section_title")
                if sec_filter and chunk.section_title:
                    if sec_filter.lower() in chunk.section_title.lower():
                        boost += 0.05
                        
                # 3. Document filename match boost
                doc_filter = metadata_filters.get("document_name")
                if doc_filter and hasattr(chunk, "document") and chunk.document:
                    if doc_filter.lower() in chunk.document.original_filename.lower():
                        boost += 0.05
            
            final_score = min(score + boost, 1.0)
            
            reranked.append({
                "chunk": chunk,
                "score": round(max(final_score, 0.0), 4)
            })
            
        # Sort by final score descending
        reranked.sort(key=lambda x: x["score"], reverse=True)
        return reranked
