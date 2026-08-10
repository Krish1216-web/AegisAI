from typing import Dict, Any, List, Optional, AsyncIterator
import time

from app.core.config import settings
from app.core.ai.base import AIProviderInterface, ChatMessage, ChatResponse, TokenUsage, EmbeddingResponse
from app.core.ai.openai_provider import OpenAIProvider
from app.core.ai.anthropic_provider import AnthropicProvider
from app.core.ai.gemini_provider import GeminiProvider
from app.core.ai.exceptions import InvalidAPIKeyException, AIProviderException

class MockProvider(AIProviderInterface):
    """
    Mock AI execution provider for test and development runs without active API keys.
    """
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
        time.sleep(0.05) # mock latency
        return ChatResponse(
            content=f"[Mock Reply for: '{messages[-1].content[:30]}'] - Running model: {model} via MockProvider.",
            model=model,
            provider="mock",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25, estimated_cost=0.0),
            latency_ms=50
        )

    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0,
        timeout: float = 30.0
    ) -> AsyncIterator[str]:
        tokens = ["This ", "is ", "a ", "streamed ", "mock ", "response ", "from ", "AegisAI."]
        for token in tokens:
            yield token

    async def generate_embeddings(
        self,
        text: str,
        model: str
    ) -> EmbeddingResponse:
        return EmbeddingResponse(
            embedding=[0.1] * 1536,
            usage=TokenUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5, estimated_cost=0.0)
        )

class ProviderFactory:
    """
    Factory resolving configured provider implementations.
    """
    @staticmethod
    def get_provider(provider_name: str) -> AIProviderInterface:
        provider_lower = provider_name.lower()
        
        if provider_lower == "openai":
            key = getattr(settings, "OPENAI_API_KEY", None)
            if not key or key == "":
                if settings.ENVIRONMENT == "dev":
                    return MockProvider()
                raise InvalidAPIKeyException("OpenAI API key is not configured in settings.")
            return OpenAIProvider(api_key=key)
            
        elif provider_lower == "anthropic":
            key = getattr(settings, "ANTHROPIC_API_KEY", None)
            if not key or key == "":
                if settings.ENVIRONMENT == "dev":
                    return MockProvider()
                raise InvalidAPIKeyException("Anthropic API key is not configured in settings.")
            return AnthropicProvider(api_key=key)
            
        elif provider_lower == "gemini":
            key = getattr(settings, "GEMINI_API_KEY", None)
            if not key or key == "":
                if settings.ENVIRONMENT == "dev":
                    return MockProvider()
                raise InvalidAPIKeyException("Google Gemini API key is not configured in settings.")
            return GeminiProvider(api_key=key)
            
        elif provider_lower == "mock":
            return MockProvider()
            
        raise AIProviderException(f"Unsupported AI provider name: {provider_name}")
