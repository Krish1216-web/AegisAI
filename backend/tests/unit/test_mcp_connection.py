import pytest
import asyncio
from unittest.mock import AsyncMock

from app.core.mcp.connection import MCPConnectionManager
from app.core.mcp.base import (
    MCPTimeoutError,
    MCPAuthError,
    MCPValidationError,
    MCPConnectionError
)
from app.models.mcp import MCPTransport

@pytest.mark.asyncio
async def test_connection_and_handshake():
    client, init_res = await MCPConnectionManager.connect_and_initialize(
        server_url="mock://test-connection",
        transport=MCPTransport.SSE,
        timeout=5.0
    )
    assert client.is_connected is True
    assert init_res.protocol_version == "2024-11-05"
    assert "MockServer" in init_res.server_name
    await client.close()

@pytest.mark.asyncio
async def test_ping_health_probe():
    res = await MCPConnectionManager.ping_health(
        server_url="mock://test-ping",
        transport=MCPTransport.SSE,
        timeout=3.0
    )
    assert res.status == "ok"
    assert res.latency_ms > 0

@pytest.mark.asyncio
async def test_retry_on_transient_failure():
    attempts = 0
    
    async def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Connection dropped by peer")
        return "success"

    result = await MCPConnectionManager.execute_with_retry(
        flaky_operation,
        max_retries=3,
        base_delay=0.01
    )
    assert result == "success"
    assert attempts == 3

@pytest.mark.asyncio
async def test_no_retry_on_auth_or_validation_errors():
    attempts = 0
    
    async def auth_failing_operation():
        nonlocal attempts
        attempts += 1
        raise MCPAuthError("Invalid API key")

    with pytest.raises(MCPAuthError):
        await MCPConnectionManager.execute_with_retry(
            auth_failing_operation,
            max_retries=3,
            base_delay=0.01
        )
    # Must immediately fail on attempt 1 without retries
    assert attempts == 1
