import uuid
import pytest
from app.core.collaboration.realtime import RealtimeConnectionManager

def test_websocket_channel_isolation():
    manager = RealtimeConnectionManager()
    user_a = uuid.uuid4()
    ws_a = uuid.uuid4()
    user_b = uuid.uuid4()
    ws_b = uuid.uuid4()

    conn_a = manager.register_connection("conn_a", user_a, ws_a, "user_a")
    conn_b = manager.register_connection("conn_b", user_b, ws_b, "user_b")

    assert conn_a.workspace_id == ws_a
    assert conn_b.workspace_id == ws_b
    assert conn_a.user_id != conn_b.user_id

    manager.unregister_connection("conn_a")
    assert manager.active_connections.get("conn_a") is None
