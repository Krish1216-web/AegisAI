import re
from typing import List, Dict, Any
from app.core.rag.base import BaseCitationSystem
from app.schemas.rag import Citation

class CitationSystem(BaseCitationSystem):
    def extract_citations(
        self,
        answer: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Citation]:
        if not answer or not candidates:
            return []

        # Extract all [num] citation marks
        matches = re.findall(r'\[(\d+)\]', answer)
        seen = set()
        citations = []

        for num_str in matches:
            num = int(num_str)
            if num in seen:
                continue
                
            # Verify bound against retrieved candidates length (1-based index)
            if 1 <= num <= len(candidates):
                seen.add(num)
                item = candidates[num - 1]
                chunk = item["chunk"]
                
                doc_id = chunk.document_id or (chunk.document.id if hasattr(chunk, "document") and chunk.document else None)
                doc_name = "Unknown Source"
                if hasattr(chunk, "document") and chunk.document:
                    doc_name = chunk.document.original_filename or chunk.document.filename
                
                snippet = chunk.content[:200]
                if len(chunk.content) > 200:
                    snippet += "..."
                    
                citations.append(Citation(
                    citation_number=num,
                    document_id=doc_id,
                    document_name=doc_name,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    snippet=snippet
                ))
                
        # Sort by citation_number
        citations.sort(key=lambda x: x.citation_number)
        return citations

    def validate_citations(
        self,
        answer: str,
        candidates: List[Dict[str, Any]]
    ) -> str:
        if not answer:
            return ""
        if not candidates:
            # Strip all citations if we have no chunks
            return re.sub(r'\s*\[\d+\]', '', answer).strip()

        # Regex replacement to strip invalid indices
        def repl(match):
            val = int(match.group(1))
            if 1 <= val <= len(candidates):
                return match.group(0) # Keep valid
            return "" # Remove invalid

        sanitized = re.sub(r'\[(\d+)\]', repl, answer)
        # Remove consecutive spaces resulting from removal
        sanitized = re.sub(r'\s{2,}', ' ', sanitized)
        return sanitized.strip()
