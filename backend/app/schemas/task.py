from pydantic import BaseModel
import uuid
from typing import List, Optional

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    workspace_id: uuid.UUID

class TaskResponse(TaskBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    class Config:
        from_attributes = True
