import uuid
import pytest
from app.core.collaboration.realtime import RealtimeConnectionManager

def test_immediate_subscription_revocation():
    manager = RealtimeConnectionManager()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    
    conn = manager.register_connection("conn_rev", user_id, ws_id, "rev_user")
    channel = f"project:{proj_id}"
    manager.subscribe_channel("conn_rev", channel)
    assert channel in conn.subscriptions
    
    # Revoke channel access
    manager.revoke_user_channel(ws_id, user_id, channel)
    assert channel not in conn.subscriptions
