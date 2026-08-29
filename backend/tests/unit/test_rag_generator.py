import pytest
from unittest.mock import MagicMock, AsyncMock
from app.core.rag.generator import RAGGenerationFlow, SAFE_FALLBACK

@pytest.mark.asyncio
async def test_generation_flow_short_circuits_on_empty_context():
    mock_ai = MagicMock()
    flow = RAGGenerationFlow(mock_ai)
    
    # Should immediately return SAFE_FALLBACK without calling AI service
    res = await flow.generate(query="what is gravity?", context="")
    assert res == SAFE_FALLBACK
    mock_ai.generate_chat.assert_not_called()

@pytest.mark.asyncio
async def test_generation_flow_calls_ai_service_with_context():
    mock_ai = MagicMock()
    mock_response = MagicMock()
    mock_response.content = " According to gravity docs, gravity pulls objects down. "
    mock_ai.generate_chat = AsyncMock(return_value=mock_response)
    
    flow = RAGGenerationFlow(mock_ai)
    res = await flow.generate(query="what is gravity?", context="Gravity pulls down [1].")
    
    assert res == "According to gravity docs, gravity pulls objects down."
    assert mock_ai.generate_chat.call_count == 1
    
    # Verify system message format
    args, kwargs = mock_ai.generate_chat.call_args
    messages = kwargs.get("messages") or args[0]
    system_msg = next(m for m in messages if m.role == "system")
    assert "Gravity pulls down [1]." in system_msg.content
