import time
from typing import List, Dict, Any, Optional, AsyncIterator
import google.generativeai as genai
from loguru import logger

from app.core.ai.base import AIProviderInterface, ChatMessage, ChatResponse, TokenUsage, EmbeddingResponse
from app.core.ai.exceptions import (
    InvalidAPIKeyException, RateLimitException, ProviderTimeoutException,
    ContextLengthExceededException, InvalidRequestException, AIProviderException
)

class GeminiProvider(AIProviderInterface):
    """
    Google Gemini async LLM execution provider.
    """
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)

    def _get_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Flash: $0.075 / 1M input, $0.30 / 1M output
        # Pro: $3.50 / 1M input, $10.50 / 1M output
        if "flash" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.075
            output_cost = (completion_tokens / 1_000_000) * 0.30
        else:
            input_cost = (prompt_tokens / 1_000_000) * 3.50
            output_cost = (completion_tokens / 1_000_000) * 10.50
        return input_cost + output_cost

    def _map_exception(self, e: Exception) -> Exception:
        err_msg = str(e)
        if "api key" in err_msg.lower() or "api_key" in err_msg.lower() or "unauthorized" in err_msg.lower():
            return InvalidAPIKeyException()
        elif "rate limit" in err_msg.lower() or "quota" in err_msg.lower() or "429" in err_msg:
            return RateLimitException()
        elif "timeout" in err_msg.lower():
            return ProviderTimeoutException()
        return AIProviderException(f"Google Gemini Provider Failure: {err_msg}")

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
        
        # Translate to Gemini format contents
        contents = []
        for msg in messages:
            role = "user" if msg.role in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [msg.content]})

        try:
            gemini_model = genai.GenerativeModel(model)
            config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=top_p
            )
            
            response = await gemini_model.generate_content_async(
                contents,
                generation_config=config
            )
            
            latency = int((time.perf_counter() - start_time) * 1000)
            
            # Request token calculations
            prompt_tokens = gemini_model.count_tokens(contents).total_tokens
            completion_tokens = gemini_model.count_tokens(response.text).total_tokens
            total_tokens = prompt_tokens + completion_tokens
            
            cost = self._get_cost(model, prompt_tokens, completion_tokens)
            
            return ChatResponse(
                content=response.text,
                model=model,
                provider="gemini",
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
        contents = []
        for msg in messages:
            role = "user" if msg.role in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [msg.content]})
            
        try:
            gemini_model = genai.GenerativeModel(model)
            config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=top_p
            )
            
            response = await gemini_model.generate_content_async(
                contents,
                generation_config=config,
                stream=True
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise self._map_exception(e)

    async def generate_embeddings(
        self,
        text: str,
        model: str
    ) -> EmbeddingResponse:
        try:
            response = genai.embed_content(
                model=model,
                content=text
            )
            return EmbeddingResponse(
                embedding=response['embedding'],
                usage=TokenUsage(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    estimated_cost=0.0
                )
            )
        except Exception as e:
            raise self._map_exception(e)
