import time
from typing import List, Dict, Any, Optional, AsyncIterator
from anthropic import AsyncAnthropic
from loguru import logger

from app.core.ai.base import AIProviderInterface, ChatMessage, ChatResponse, TokenUsage, EmbeddingResponse
from app.core.ai.exceptions import (
    InvalidAPIKeyException, RateLimitException, ProviderTimeoutException,
    ContextLengthExceededException, InvalidRequestException, AIProviderException
)

class AnthropicProvider(AIProviderInterface):
    """
    Anthropic Claude async LLM execution provider.
    """
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    def _get_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Haiku: $0.25 / 1M input, $1.25 / 1M output
        # Sonnet 3.5: $3.00 / 1M input, $15.00 / 1M output
        if "haiku" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.25
            output_cost = (completion_tokens / 1_000_000) * 1.25
        else:
            input_cost = (prompt_tokens / 1_000_000) * 3.00
            output_cost = (completion_tokens / 1_000_000) * 15.00
        return input_cost + output_cost

    def _map_exception(self, e: Exception) -> Exception:
        err_msg = str(e)
        if "api_key" in err_msg.lower() or "authentication" in err_msg.lower() or "401" in err_msg:
            return InvalidAPIKeyException()
        elif "rate limit" in err_msg.lower() or "429" in err_msg:
            return RateLimitException()
        elif "timeout" in err_msg.lower():
            return ProviderTimeoutException()
        elif "context_length" in err_msg.lower() or "max_tokens" in err_msg.lower():
            return ContextLengthExceededException()
        return AIProviderException(f"Anthropic Provider Failure: {err_msg}")

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
        start_time = time.perf_counter()
        
        # Anthropic extracts system messages to top level parameter
        system_content = ""
        user_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        try:
            params = {
                "model": model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "timeout": timeout
            }
            if system_content:
                params["system"] = system_content
            
            # Tools not fully handled for mock tests
            
            response = await self.client.messages.create(**params)
            
            latency = int((time.perf_counter() - start_time) * 1000)
            
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens
            
            cost = self._get_cost(model, prompt_tokens, completion_tokens)
            
            # Extract content text
            content_text = ""
            if response.content and hasattr(response.content[0], "text"):
                content_text = response.content[0].text
                
            return ChatResponse(
                content=content_text,
                model=model,
                provider="anthropic",
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=cost
                ),
                latency_ms=latency
            )
        except Exception as e:
            raise self._map_exception(e)

    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0,
        timeout: float = 30.0
    ) -> AsyncIterator[str]:
        system_content = ""
        user_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})
                
        try:
            params = {
                "model": model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "timeout": timeout
            }
            if system_content:
                params["system"] = system_content
                
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise self._map_exception(e)

    async def generate_embeddings(
        self,
        text: str,
        model: str
    ) -> EmbeddingResponse:
        # Anthropic does not natively expose public text embedding endpoint APIs.
        # Failover or return mock vector representation.
        raise AIProviderException("Anthropic provider does not support native text embeddings.")
