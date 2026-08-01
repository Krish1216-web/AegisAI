from pydantic import BaseModel
import uuid
from typing import List, Optional

class ConversationBase(BaseModel):
    title: str

class ConversationCreate(ConversationBase):
    workspace_id: uuid.UUID

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class ConversationResponse(ConversationBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    sender_type: str
    content: str

class MessageCreate(MessageBase):
    conversation_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None

class MessageResponse(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    class Config:
        from_attributes = True
