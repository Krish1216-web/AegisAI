import uuid
import pytest
from app.core.collaboration.realtime import (
    RealtimeConnectionManager,
    MAX_WS_CONNECTIONS_PER_USER,
    MAX_WS_CONNECTIONS_PER_WORKSPACE,
    MAX_WS_SUBSCRIPTIONS_PER_CONNECTION
)

def test_connection_registration_and_limits():
    manager = RealtimeConnectionManager()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    
    # 1. Register connection
    conn = manager.register_connection("conn_1", user_id, ws_id, "testuser")
    assert conn.connection_id == "conn_1"
    assert f"workspace:{ws_id}" in conn.subscriptions
    assert "conn_1" in manager.active_connections
    
    # 2. Unregister
    unreg = manager.unregister_connection("conn_1")
    assert unreg is not None
    assert "conn_1" not in manager.active_connections
