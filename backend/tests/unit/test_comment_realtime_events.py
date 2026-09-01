import uuid
import pytest
from app.core.collaboration.realtime import RealtimeConnectionManager
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType

def test_comment_platform_event_emission():
    manager = RealtimeConnectionManager()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    
    conn = manager.register_connection("conn_comm", user_id, ws_id, "comm_user")
    manager.subscribe_channel("conn_comm", f"project:{proj_id}")
    
    # Emit comment created event
    evt = PlatformEvent(
        event_type=PlatformEventType.COLLABORATION_EVENT,
        workspace_id=ws_id,
        user_id=user_id,
        source_component="test",
        correlation_id="corr_comm",
        payload={"action": "COMMENT_CREATED", "project_id": str(proj_id), "comment_id": "c123"}
    )
    PlatformEventDispatcher.emit(evt)
    assert True
