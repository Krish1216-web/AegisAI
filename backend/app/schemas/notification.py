from pydantic import BaseModel
import uuid
from typing import List, Optional

class NotificationBase(BaseModel):
    title: str
    message: str
    is_read: bool

class NotificationCreate(NotificationBase):
    user_id: uuid.UUID

class NotificationResponse(NotificationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    class Config:
        from_attributes = True
