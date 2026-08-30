from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.services.extractors.base import ExtractedDocument

class ChunkResult(BaseModel):
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    start_offset: int
    end_offset: int
    token_count: int
    character_count: int

class BaseTokenizer(ABC):
    @abstractmethod
    def encode(self, text: str) -> list:
        pass

    @abstractmethod
    def decode(self, tokens: list) -> str:
        pass

    def count_tokens(self, text: str) -> int:
        return len(self.encode(text))

class ApproximateTokenizer(BaseTokenizer):
    """
    Fallback tokenizer utilizing character length heuristics (1 token ≈ 4 characters).
    Requires no heavy external libraries or remote downloads.
    """
    def encode(self, text: str) -> list:
        if not text:
            return []
        return [text[i:i+4] for i in range(0, len(text), 4)]

    def decode(self, tokens: list) -> str:
        return "".join(tokens)

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, doc: ExtractedDocument, tokenizer: BaseTokenizer) -> List[ChunkResult]:
        """
        Splits an ExtractedDocument's contents into structured database-ready ChunkResult elements.
        """
        pass
