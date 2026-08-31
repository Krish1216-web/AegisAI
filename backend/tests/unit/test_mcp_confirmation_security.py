import pytest
import uuid
import datetime
import json
from app.services.mcp.mcp_tool_executor import (
    generate_tool_confirmation_token,
    verify_and_consume_confirmation_token
)

def test_confirmation_token_lifecycle_and_single_use():
    u_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    args = {"action": "delete_record", "id": 101}

    # 1. Generate token
    token = generate_tool_confirmation_token(u_id, ws_id, tool_id, args, expires_in_seconds=60)
    assert token is not None

    # 2. Consume token successfully
    is_valid = verify_and_consume_confirmation_token(token, u_id, ws_id, tool_id, args)
    assert is_valid is True

    # 3. Attempt replay with same token -> Must be rejected (single-use)
    replay_valid = verify_and_consume_confirmation_token(token, u_id, ws_id, tool_id, args)
    assert replay_valid is False

def test_confirmation_token_argument_tampering_rejected():
    u_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    orig_args = {"path": "/safe/dir/file.txt"}
    tampered_args = {"path": "/etc/shadow"}

    token = generate_tool_confirmation_token(u_id, ws_id, tool_id, orig_args, expires_in_seconds=60)

    # Attempt to consume token with modified arguments -> Must fail
    is_valid = verify_and_consume_confirmation_token(token, u_id, ws_id, tool_id, tampered_args)
    assert is_valid is False

def test_confirmation_token_wrong_tenant_or_user_rejected():
    u_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    args = {"command": "restart"}

    token = generate_tool_confirmation_token(u_id, ws_id, tool_id, args, expires_in_seconds=60)

    # Wrong user
    assert verify_and_consume_confirmation_token(token, uuid.uuid4(), ws_id, tool_id, args) is False

    # Regenerate token and test wrong workspace
    token2 = generate_tool_confirmation_token(u_id, ws_id, tool_id, args, expires_in_seconds=60)
    assert verify_and_consume_confirmation_token(token2, u_id, uuid.uuid4(), tool_id, args) is False

def test_confirmation_token_expired_rejected():
    u_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    args = {"operation": "purge"}

    # Generate token that expires in -10 seconds
    token = generate_tool_confirmation_token(u_id, ws_id, tool_id, args, expires_in_seconds=-10)
    assert verify_and_consume_confirmation_token(token, u_id, ws_id, tool_id, args) is False
