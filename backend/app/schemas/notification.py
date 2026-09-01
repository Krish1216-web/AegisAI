import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class NotificationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    recipient_user_id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    type: str
    title: str
    body: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None
    comment_id: Optional[uuid.UUID] = None
    status: str
    read_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    page: int = 1
    page_size: int = 50
    notifications: List[NotificationResponse] = Field(default_factory=list)

class UnreadCountResponse(BaseModel):
    unread_count: int

class NotificationPreferenceItem(BaseModel):
    notification_type: str
    in_app_enabled: bool = True
    email_enabled: bool = True
    push_enabled: bool = True

class NotificationPreferenceResponse(BaseModel):
    user_id: uuid.UUID
    preferences: List[NotificationPreferenceItem]

class NotificationPreferenceUpdate(BaseModel):
    notification_type: str
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
