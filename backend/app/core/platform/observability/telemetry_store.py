import uuid
import datetime
import math
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
from threading import Lock

from app.core.platform.events import PlatformEvent, PlatformEventType, PlatformEventDispatcher
from app.core.mcp.security import CredentialStore

MAX_EVENTS_PER_WORKSPACE = 2000

class PlatformTelemetryStore:
    """
    Tenant-isolated in-memory telemetry buffer for platform events and execution traces.
    Safely indexes events by workspace with bounded memory and thread safety.
    """
    _lock = Lock()
    _events_by_workspace: Dict[uuid.UUID, deque] = defaultdict(lambda: deque(maxlen=MAX_EVENTS_PER_WORKSPACE))
    _initialized = False

    @classmethod
    def initialize(cls) -> None:
        with cls._lock:
            if not cls._initialized:
                # Subscribe to all PlatformEvent types
                for event_type in PlatformEventType:
                    PlatformEventDispatcher.subscribe(event_type, cls.record_event)
                cls._initialized = True

    @classmethod
    def record_event(cls, event: PlatformEvent) -> None:
        if not event or not event.workspace_id:
            return
        
        # Sanitize payload
        clean_event = PlatformEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            correlation_id=event.correlation_id,
            workspace_id=event.workspace_id,
            user_id=event.user_id,
            source_component=event.source_component,
            payload=CredentialStore.redact_sensitive_dict(event.payload),
            schema_version=event.schema_version
        )

        with cls._lock:
            cls._events_by_workspace[event.workspace_id].append(clean_event)

    @classmethod
    def get_events(
        cls,
        workspace_id: uuid.UUID,
        since_dt: Optional[datetime.datetime] = None,
        event_type: Optional[PlatformEventType] = None,
        correlation_id: Optional[str] = None
    ) -> List[PlatformEvent]:
        with cls._lock:
            q = list(cls._events_by_workspace.get(workspace_id, []))

        results = []
        for evt in q:
            if since_dt and evt.timestamp < since_dt:
                continue
            if event_type and evt.event_type != event_type:
                continue
            if correlation_id and evt.correlation_id != correlation_id:
                continue
            results.append(evt)

        return sorted(results, key=lambda e: e.timestamp)

    @classmethod
    def clear(cls, workspace_id: Optional[uuid.UUID] = None) -> None:
        with cls._lock:
            if workspace_id:
                if workspace_id in cls._events_by_workspace:
                    cls._events_by_workspace[workspace_id].clear()
            else:
                cls._events_by_workspace.clear()

    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        """
        Deterministic nearest-rank / linear interpolation percentile calculation.
        """
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(float(sorted_vals[int(k)]), 2)
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return round(float(d0 + d1), 2)
