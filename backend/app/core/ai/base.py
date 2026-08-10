import abc
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncIterator

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0

class ChatMessage(BaseModel):
    role: str # user | assistant | system
    content: str

class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: TokenUsage
    latency_ms: int

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    usage: TokenUsage

class AIProviderInterface(abc.ABC):
    """
    Independent interface for interacting with LLM models.
    """
    @abc.abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0,
        timeout: float = 30.0,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        pass

    @abc.abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0,
        timeout: float = 30.0
    ) -> AsyncIterator[str]:
        pass

    @abc.abstractmethod
    async def generate_embeddings(
        self,
        text: str,
        model: str
    ) -> EmbeddingResponse:
        pass
