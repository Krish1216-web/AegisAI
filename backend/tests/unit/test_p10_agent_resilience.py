import pytest
from app.core.ai.exceptions import AIProviderException, RateLimitException, ProviderTimeoutException
from app.core.agent.exceptions import AgentExecutionError, AgentTimeout

def test_ai_provider_exceptions():
    err = ProviderTimeoutException("Connection timeout")
    assert err.status_code == 504
    assert err.code == "PROVIDER_TIMEOUT"
    assert "Connection timeout" in str(err)
    
    rate_err = RateLimitException("Rate limit exceeded")
    assert rate_err.status_code == 429
    assert rate_err.code == "RATE_LIMIT_EXCEEDED"

def test_agent_execution_exceptions():
    exec_err = AgentExecutionError("Tool execution failed in step 3")
    assert exec_err.code == "AGENT_EXECUTION_ERROR"
    assert "Tool execution failed" in str(exec_err)

    timeout_err = AgentTimeout("Execution exceeded limit")
    assert timeout_err.code == "AGENT_TIMEOUT"
