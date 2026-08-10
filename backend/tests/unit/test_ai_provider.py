import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, AsyncIterator
import asyncio

from app.core.ai.base import ChatMessage, ChatResponse, TokenUsage
from app.core.ai.factory import ProviderFactory, MockProvider
from app.core.ai.exceptions import InvalidAPIKeyException, RateLimitException, AIProviderException
from app.services.ai_service import AIService

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_redis():
    client = MagicMock()
    client.get.return_value = None
    return client

def test_provider_factory_mock():
    # Factory should return MockProvider in dev environment if key is empty
    with patch("app.core.config.settings.ENVIRONMENT", "dev"):
        with patch("app.core.config.settings.OPENAI_API_KEY", ""):
            provider = ProviderFactory.get_provider("openai")
            assert isinstance(provider, MockProvider)

def test_provider_factory_invalid():
    # If prod environment and key missing, raise exception
    with patch("app.core.config.settings.ENVIRONMENT", "prod"):
        with patch("app.core.config.settings.OPENAI_API_KEY", ""):
            with pytest.raises(InvalidAPIKeyException):
                ProviderFactory.get_provider("openai")

@pytest.mark.asyncio
async def test_ai_service_cache_hit(mock_db, mock_redis):
    # Mock cache hit in Redis
    cached_data = {
        "content": "This response is from Redis cache",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "estimated_cost": 0.0001
        }
    }
    mock_redis.get.return_value = '{"content": "This response is from Redis cache", "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "estimated_cost": 0.0001}}'
    
    ai_service = AIService(db=mock_db, redis_client=mock_redis)
    messages = [ChatMessage(role="user", content="Hello")]
    
    response = await ai_service.generate_chat(
        messages=messages,
        provider="mock",
        model="mock-model",
        bypass_cache=False
    )
    
    assert response.content == "This response is from Redis cache"
    assert response.usage.total_tokens == 30
    assert response.latency_ms == 0  # Cache returns 0 latency
    mock_redis.get.assert_called_once()

@pytest.mark.asyncio
async def test_ai_service_fallback_flow(mock_db, mock_redis):
    # Test that if OpenAI throws a RateLimitException or key error, it falls back to Gemini
    ai_service = AIService(db=mock_db, redis_client=mock_redis)
    messages = [ChatMessage(role="user", content="Hello")]
    
    openai_mock = MagicMock()
    openai_mock.generate_chat_completion = AsyncMock(side_effect=RateLimitException("OpenAI rate limit"))
    
    gemini_mock = MagicMock()
    gemini_mock.generate_chat_completion = AsyncMock(return_value=ChatResponse(
        content="Hello from Gemini fallback!",
        model="gemini-1.5-flash",
        provider="gemini",
        usage=TokenUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15, estimated_cost=0.0),
        latency_ms=100
    ))
    
    def mock_get_provider(prov_name: str):
        if prov_name == "openai":
            return openai_mock
        elif prov_name == "gemini":
            return gemini_mock
        return MockProvider()
        
    with patch("app.services.ai_service.ProviderFactory.get_provider", side_effect=mock_get_provider):
        response = await ai_service.generate_chat(
            messages=messages,
            provider="openai",
            model="gpt-4o-mini",
            bypass_cache=True
        )
        
        assert response.content == "Hello from Gemini fallback!"
        assert response.provider == "gemini"
        # OpenAI was called first and failed, then Gemini succeeded
        assert openai_mock.generate_chat_completion.call_count == 3
        gemini_mock.generate_chat_completion.assert_called_once()
