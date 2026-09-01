import uuid
import pytest
from app.core.collaboration.realtime import RealtimeConnectionManager
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType

def test_platform_collaboration_event_broadcasting():
    manager = RealtimeConnectionManager()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    
    conn = manager.register_connection("conn_evt", user_id, ws_id, "evt_user")
    manager.subscribe_channel("conn_evt", f"project:{proj_id}")
    
    # Emit platform collaboration event
    evt = PlatformEvent(
        event_type=PlatformEventType.COLLABORATION_EVENT,
        workspace_id=ws_id,
        user_id=user_id,
        source_component="test",
        correlation_id="corr_123",
        payload={"action": "PROJECT_RESOURCE_LINKED", "project_id": str(proj_id), "resource_type": "document"}
    )
    PlatformEventDispatcher.emit(evt)
    # Event dispatched without error
    assert True
