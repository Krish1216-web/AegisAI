from pydantic import BaseModel
import uuid
from typing import List, Optional

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    organization_id: uuid.UUID

class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    title: str

class ConversationCreate(ConversationBase):
    workspace_id: uuid.UUID

class ConversationResponse(ConversationBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    class Config:
        from_attributes = True
