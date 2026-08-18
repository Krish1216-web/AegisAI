from typing import List
from app.services.chunking.base import ChunkResult, ApproximateTokenizer
from app.services.chunking.recursive import RecursiveCharacterChunker
from app.services.extractors.base import ExtractedDocument
from app.core.config import settings

class DocumentChunkerService:
    @staticmethod
    def chunk_document(doc: ExtractedDocument) -> List[ChunkResult]:
        """
        Chunks the parsed document utilizing the default recursive character splitter.
        Uses ApproximateTokenizer for token boundary sizing.
        """
        tokenizer = ApproximateTokenizer()
        chunker = RecursiveCharacterChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        return chunker.chunk(doc, tokenizer)
