import uuid
from app.core.platform.events import (
    PlatformEventType,
    PlatformEvent,
    PlatformEventDispatcher
)

def test_platform_event_emission_and_dispatch():
    received_events = []

    def test_handler(event: PlatformEvent):
        received_events.append(event)

    PlatformEventDispatcher.clear_handlers()
    PlatformEventDispatcher.subscribe(PlatformEventType.SECURITY_EVENT, test_handler)

    ws_id = uuid.uuid4()
    evt = PlatformEvent(
        event_type=PlatformEventType.SECURITY_EVENT,
        correlation_id="corr_test_123",
        workspace_id=ws_id,
        source_component="test_suite",
        payload={"action": "token_check", "status": "passed"}
    )

    PlatformEventDispatcher.emit(evt)

    assert len(received_events) == 1
    assert received_events[0].event_type == PlatformEventType.SECURITY_EVENT
    assert received_events[0].correlation_id == "corr_test_123"
    assert received_events[0].payload["action"] == "token_check"
