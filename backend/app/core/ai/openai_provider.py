import time
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from loguru import logger
import jwt

from app.core.ai.base import AIProviderInterface, ChatMessage, ChatResponse, TokenUsage, EmbeddingResponse
from app.core.ai.exceptions import (
    InvalidAPIKeyException, RateLimitException, ProviderTimeoutException,
    ContextLengthExceededException, InvalidRequestException, AIProviderException
)

class OpenAIProvider(AIProviderInterface):
    """
    OpenAI async LLM execution provider.
    """
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    def _get_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Mini: $0.15 / 1M input, $0.60 / 1M output
        # Standard GPT-4o: $5.00 / 1M input, $15.00 / 1M output
        if "mini" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.15
            output_cost = (completion_tokens / 1_000_000) * 0.60
        else:
            input_cost = (prompt_tokens / 1_000_000) * 5.00
            output_cost = (completion_tokens / 1_000_000) * 15.00
        return input_cost + output_cost

    def _map_exception(self, e: Exception) -> Exception:
        err_msg = str(e)
        if "api_key" in err_msg.lower() or "incorrect api key" in err_msg.lower() or "401" in err_msg:
            return InvalidAPIKeyException()
        elif "rate limit" in err_msg.lower() or "429" in err_msg:
            return RateLimitException()
        elif "timeout" in err_msg.lower():
            return ProviderTimeoutException()
        elif "context_length" in err_msg.lower() or "maximum context length" in err_msg.lower():
            return ContextLengthExceededException()
        return AIProviderException(f"OpenAI Provider Failure: {err_msg}")

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
        
        # Prepare OpenAI format messages list
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        try:
            params = {
                "model": model,
                "messages": formatted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "timeout": timeout
            }
            if tools:
                params["tools"] = tools

            response: ChatCompletion = await self.client.chat.completions.create(**params)
            
            latency = int((time.perf_counter() - start_time) * 1000)
            
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            cost = self._get_cost(model, prompt_tokens, completion_tokens)
            
            return ChatResponse(
                content=response.choices[0].message.content or "",
                model=model,
                provider="openai",
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
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                timeout=timeout,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise self._map_exception(e)

    async def generate_embeddings(
        self,
        text: str,
        model: str
    ) -> EmbeddingResponse:
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            cost = (prompt_tokens / 1_000_000) * 0.02 # static embedding estimation
            return EmbeddingResponse(
                embedding=response.data[0].embedding,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=0,
                    total_tokens=prompt_tokens,
                    estimated_cost=cost
                )
            )
        except Exception as e:
            raise self._map_exception(e)
