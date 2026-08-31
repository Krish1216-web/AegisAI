import pytest
import asyncio
import uuid
from app.services.mcp.mcp_tool_executor import (
    generate_tool_confirmation_token,
    verify_and_consume_confirmation_token
)

@pytest.mark.asyncio
async def test_concurrent_confirmation_token_consumption_race():
    """
    Ensures that when multiple simultaneous asynchronous tasks attempt to consume
    the same confirmation token, exactly ONE succeeds and all others are rejected.
    """
    u_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    args = {"transfer_amount": 5000}

    token = generate_tool_confirmation_token(u_id, ws_id, tool_id, args, expires_in_seconds=60)

    async def attempt_consume():
        await asyncio.sleep(0.01) # Synchronize event loop timing
        return verify_and_consume_confirmation_token(token, u_id, ws_id, tool_id, args)

    # Launch 25 concurrent consume attempts
    results = await asyncio.gather(*[attempt_consume() for _ in range(25)])

    # Exactly 1 success, 24 failures
    success_count = sum(1 for r in results if r is True)
    failure_count = sum(1 for r in results if r is False)

    assert success_count == 1
    assert failure_count == 24
