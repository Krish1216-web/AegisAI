import time
import hashlib
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from sqlalchemy.orm import Session
import redis
from loguru import logger

from app.core.config import settings
from app.core.ai.base import ChatMessage, ChatResponse, TokenUsage, EmbeddingResponse
from app.core.ai.factory import ProviderFactory
from app.core.ai.exceptions import AIProviderException, InvalidAPIKeyException, InvalidRequestException
from app.models.ai import AIRequestLog, ProviderHealthStatus

class AIService:
    """
    AIService coordinates LLM requests, caching, backoff retries, and provider fallbacks.
    """
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    def _get_cache_key(self, messages: List[ChatMessage], model: str, user_id: Any) -> str:
        serialized = json.dumps([{"role": m.role, "content": m.content} for m in messages]) + f":{model}:{user_id}"
        hasher = hashlib.sha256()
        hasher.update(serialized.encode("utf-8"))
        return f"aegis:ai_cache:{hasher.hexdigest()}"

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        cached = self.redis.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                return None
        return None

    def _set_cached_response(self, cache_key: str, data: Dict[str, Any]):
        try:
            self.redis.setex(cache_key, 3600, json.dumps(data)) # cache for 1 hour
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    def _log_request(
        self,
        user_id: Optional[Any],
        provider: str,
        model: str,
        usage: TokenUsage,
        latency: int,
        success: bool,
        error_msg: Optional[str] = None
    ):
        try:
            log = AIRequestLog(
                user_id=user_id,
                provider=provider,
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                cost=usage.estimated_cost,
                latency_ms=latency,
                success=success,
                error_message=error_msg
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI request metadata: {e}")

    async def generate_chat(
        self,
        messages: List[ChatMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[Any] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        bypass_cache: bool = False
    ) -> ChatResponse:
        active_provider = provider or settings.DEFAULT_AI_PROVIDER
        active_model = model or settings.DEFAULT_AI_MODEL
        
        # 1. Caching check
        cache_key = self._get_cache_key(messages, active_model, user_id)
        if not bypass_cache:
            cached = self._get_cached_response(cache_key)
            if cached:
                logger.info(f"AI response resolved from Redis cache. Key: {cache_key}")
                return ChatResponse(
                    content=cached["content"],
                    model=active_model,
                    provider=active_provider,
                    usage=TokenUsage(**cached["usage"]),
                    latency_ms=0
                )

        # 2. Execution with retries and fallbacks
        providers_sequence = [active_provider]
        # Build fallback list if OpenAI was default
        if active_provider == "openai":
            providers_sequence.extend(["gemini", "anthropic"])
        elif active_provider == "gemini":
            providers_sequence.extend(["openai", "anthropic"])
            
        last_exception = None
        for current_prov in providers_sequence:
            try:
                provider_client = ProviderFactory.get_provider(current_prov)
                
                # Retry logic for retryable errors (429, Timeouts, network drop)
                retries = 3
                delay = 1.0
                for attempt in range(retries):
                    try:
                        response = await provider_client.generate_chat_completion(
                            messages=messages,
                            model=active_model if current_prov == active_provider else self._get_fallback_model(current_prov),
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        # Log and cache successful execution
                        self._log_request(user_id, current_prov, response.model, response.usage, response.latency_ms, True)
                        
                        if not bypass_cache:
                            self._set_cached_response(cache_key, {
                                "content": response.content,
                                "usage": response.usage.model_dump()
                            })
                            
                        return response
                    except (InvalidAPIKeyException, InvalidRequestException) as e:
                        # Permanent client errors, do not retry
                        raise e
                    except Exception as e:
                        if attempt == retries - 1:
                            raise e
                        logger.warning(f"Attempt {attempt+1} failed for {current_prov}. Retrying in {delay}s... Error: {e}")
                        await asyncio.sleep(delay)
                        delay *= 2  # Exponential backoff
                        
            except Exception as e:
                logger.error(f"Provider {current_prov} execution failed. Error: {e}")
                self._log_request(user_id, current_prov, active_model, TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0), 0, False, str(e))
                last_exception = e
                # Fall through to next provider in sequence

        if last_exception:
            raise last_exception
        raise AIProviderException("All configured AI providers failed.")

    def _get_fallback_model(self, provider: str) -> str:
        if provider == "openai":
            return "gpt-4o-mini"
        elif provider == "gemini":
            return "gemini-1.5-flash"
        elif provider == "anthropic":
            return "claude-3-haiku-20240307"
        return "mock"

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncIterator[str]:
        active_provider = provider or settings.DEFAULT_AI_PROVIDER
        active_model = model or settings.DEFAULT_AI_MODEL
        
        try:
            provider_client = ProviderFactory.get_provider(active_provider)
            async for chunk in provider_client.stream_chat_completion(
                messages=messages,
                model=active_model,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming failed for provider {active_provider}. Error: {e}")
            raise e
