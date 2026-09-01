import uuid
import pytest
from app.core.collaboration.realtime import RealtimeConnectionManager

def test_presence_lifecycle_updates():
    manager = RealtimeConnectionManager()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    
    conn = manager.register_connection("conn_pres", user_id, ws_id, "pres_user")
    assert conn.presence_status == "online"
    
    # Update to away
    res = manager.update_presence("conn_pres", "away")
    assert res is not None
    assert res["status"] == "away"
    assert conn.presence_status == "away"
