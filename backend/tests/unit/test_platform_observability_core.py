import pytest
import uuid
import datetime
from app.core.platform.events import PlatformEvent, PlatformEventType
from app.core.platform.observability.models import (
    TimeWindow,
    CapabilityHealth,
    BottleneckClassification,
    AlertSeverity
)
from app.core.platform.observability.telemetry_store import PlatformTelemetryStore

def test_time_window_parsing_and_validation():
    # Valid time windows
    assert TimeWindow.to_timedelta("1h") == datetime.timedelta(hours=1)
    assert TimeWindow.to_timedelta("24h") == datetime.timedelta(hours=24)
    assert TimeWindow.to_timedelta("7d") == datetime.timedelta(days=7)
    assert TimeWindow.to_timedelta("30d") == datetime.timedelta(days=30)

    # Invalid time window
    with pytest.raises(ValueError, match="Unsupported time window"):
        TimeWindow.to_timedelta("100d")

def test_percentile_calculations():
    # Empty list
    assert PlatformTelemetryStore.calculate_percentile([], 50.0) == 0.0

    # Single element
    assert PlatformTelemetryStore.calculate_percentile([100.0], 50.0) == 100.0
    assert PlatformTelemetryStore.calculate_percentile([100.0], 95.0) == 100.0

    # Deterministic values
    vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50 = PlatformTelemetryStore.calculate_percentile(vals, 50.0)
    p95 = PlatformTelemetryStore.calculate_percentile(vals, 95.0)
    p99 = PlatformTelemetryStore.calculate_percentile(vals, 99.0)

    assert p50 == 55.0
    assert p95 >= 90.0
    assert p99 >= 95.0

def test_telemetry_store_event_recording_and_sanitization():
    ws_id = uuid.uuid4()
    PlatformTelemetryStore.clear(ws_id)

    event = PlatformEvent(
        event_type=PlatformEventType.LIFECYCLE_EVENT,
        correlation_id="corr_test",
        workspace_id=ws_id,
        source_component="test_component",
        payload={
            "api_key": "sk-secret123456789",
            "password": "SuperSecretPassword123!",
            "message": "User session token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeak"
        }
    )

    PlatformTelemetryStore.record_event(event)
    events = PlatformTelemetryStore.get_events(ws_id)

    assert len(events) == 1
    clean_payload = events[0].payload
    assert clean_payload["api_key"] == "[REDACTED]"
    assert clean_payload["password"] == "[REDACTED]"
    assert "[REDACTED]" in clean_payload["message"]
