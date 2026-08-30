import abc
from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from app.models.document import DocumentChunk
from app.schemas.rag import Citation

class BaseRetriever(abc.ABC):
    @abc.abstractmethod
    async def retrieve(
        self,
        db: Session,
        query: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant document chunks for the query within tenant bounds.
        Returns a list of dicts with keys: 'chunk' (DocumentChunk) and 'score' (float).
        """
        pass

class BaseReranker(abc.ABC):
    @abc.abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Re-scores and re-ranks retrieved chunks.
        Returns sorted list of dicts with keys: 'chunk' and 'score'.
        """
        pass

class BaseContextBuilder(abc.ABC):
    @abc.abstractmethod
    def build_context(
        self,
        candidates: List[Dict[str, Any]],
        max_tokens: int = 4000
    ) -> str:
        """
        Constructs context blocks from re-ranked chunks within limits.
        """
        pass

class BaseCitationSystem(abc.ABC):
    @abc.abstractmethod
    def extract_citations(
        self,
        answer: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Citation]:
        """
        Extracts citations matching chunk references in the answer.
        """
        pass

    @abc.abstractmethod
    def validate_citations(
        self,
        answer: str,
        candidates: List[Dict[str, Any]]
    ) -> str:
        """
        Validates citations in the answer and returns a sanitized text with invalid ones removed.
        """
        pass

class BaseGenerationFlow(abc.ABC):
    @abc.abstractmethod
    async def generate(
        self,
        query: str,
        context: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generates grounded answers or returns a safe statement on insufficient context.
        """
        pass
