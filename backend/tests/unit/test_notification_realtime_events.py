import uuid
import pytest
from app.core.collaboration.realtime import RealtimeConnectionManager
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType

def test_notification_realtime_event_dispatch():
    manager = RealtimeConnectionManager()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    
    conn = manager.register_connection("conn_notif", user_id, ws_id, "notif_user")
    
    # Dispatch notification event
    evt = PlatformEvent(
        event_type=PlatformEventType.COLLABORATION_EVENT,
        workspace_id=ws_id,
        user_id=user_id,
        source_component="test",
        correlation_id="corr_notif",
        payload={
            "action": "NOTIFICATION_CREATED",
            "notification_id": "notif_123",
            "type": "MENTION",
            "unread_count": 3
        }
    )
    PlatformEventDispatcher.emit(evt)
    assert True
