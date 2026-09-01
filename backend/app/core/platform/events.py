import uuid
import datetime
import enum
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field
from loguru import logger

class PlatformEventType(str, enum.Enum):
    AGENT_EVENT = "agent_event"
    RAG_EVENT = "rag_event"
    GRAPH_EVENT = "graph_event"
    MCP_EVENT = "mcp_event"
    WORKFLOW_EVENT = "workflow_event"
    SECURITY_EVENT = "security_event"
    REASONING_EVENT = "reasoning_event"
    INTELLIGENCE_EVENT = "intelligence_event"
    LIFECYCLE_EVENT = "lifecycle_event"
    SYSTEM_EVENT = "system_event"
    COLLABORATION_EVENT = "collaboration_event"

class PlatformEvent(BaseModel):
    """
    Strongly typed event envelope for Phase 8 platform subsystems.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: PlatformEventType
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    correlation_id: str
    workspace_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    source_component: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "1.0.0"

class PlatformEventDispatcher:
    """
    Synchronous / asynchronous in-memory event dispatcher with hooks.
    Extensible to Redis PubSub and SSE pipelines.
    """
    _handlers: Dict[PlatformEventType, List[Callable[[PlatformEvent], None]]] = {}

    @classmethod
    def subscribe(cls, event_type: PlatformEventType, handler: Callable[[PlatformEvent], None]) -> None:
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    @classmethod
    def emit(cls, event: PlatformEvent) -> None:
        logger.debug(f"[PlatformEvent] {event.event_type.value} from {event.source_component} (corr: {event.correlation_id})")
        handlers = cls._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Error executing event handler for {event.event_type.value}: {e}")

    @classmethod
    def clear_handlers(cls) -> None:
        cls._handlers.clear()
