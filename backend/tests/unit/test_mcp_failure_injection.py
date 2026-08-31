import pytest
import uuid
from app.core.mcp.connection import MCPConnectionManager
from app.core.mcp.base import (
    MCPAuthError,
    MCPValidationError,
    MCPTimeoutError,
    MCPClientError
)

@pytest.mark.asyncio
async def test_non_retriable_auth_and_validation_errors():
    call_count = 0

    async def faulty_auth_op():
        nonlocal call_count
        call_count += 1
        raise MCPAuthError("Invalid API key")

    # MCPAuthError must fail immediately with 0 retries (call_count == 1)
    with pytest.raises(MCPAuthError):
        await MCPConnectionManager.execute_with_retry(faulty_auth_op, max_retries=3)

    assert call_count == 1

@pytest.mark.asyncio
async def test_retriable_network_error_with_eventual_success():
    call_count = 0

    async def flaky_network_op():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionResetError("Connection reset by peer")
        return {"status": "SUCCESS", "attempts": call_count}

    res = await MCPConnectionManager.execute_with_retry(
        flaky_network_op,
        max_retries=3,
        base_delay=0.01
    )
    assert res["status"] == "SUCCESS"
    assert res["attempts"] == 3
