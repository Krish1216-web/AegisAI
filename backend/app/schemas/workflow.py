from pydantic import BaseModel
import uuid
from typing import List, Optional

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkflowCreate(WorkflowBase):
    workspace_id: uuid.UUID

class WorkflowResponse(WorkflowBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    class Config:
        from_attributes = True

class WorkflowNodeBase(BaseModel):
    name: str
    node_type: str
    config_data: Optional[str] = None

class WorkflowNodeCreate(WorkflowNodeBase):
    workflow_id: uuid.UUID

class WorkflowNodeResponse(WorkflowNodeBase):
    id: uuid.UUID
    workflow_id: uuid.UUID
    class Config:
        from_attributes = True
