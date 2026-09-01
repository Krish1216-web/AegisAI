import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class WSClientMessage(BaseModel):
    type: str = Field(..., description="subscribe, unsubscribe, ping, presence")
    channel: Optional[str] = None
    status: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

class WSServerMessage(BaseModel):
    type: str = Field(..., description="subscription_ack, pong, error, event, presence")
    channel: Optional[str] = None
    status: Optional[str] = None
    event_id: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class RealtimeEventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: f"rt_evt_{uuid.uuid4().hex[:12]}")
    event_type: str
    scope: str = Field(..., description="workspace, team, project")
    workspace_id: uuid.UUID
    channel: str
    actor_id: Optional[uuid.UUID] = None
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:8]}")
    payload: Dict[str, Any] = Field(default_factory=dict)
