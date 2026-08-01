from pydantic import BaseModel
import uuid
from typing import List, Optional

class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    organization_id: uuid.UUID

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None

class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    class Config:
        from_attributes = True

class WorkspaceMemberBase(BaseModel):
    role: str

class WorkspaceMemberCreate(WorkspaceMemberBase):
    workspace_id: uuid.UUID
    user_id: uuid.UUID

class WorkspaceMemberResponse(WorkspaceMemberBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    class Config:
        from_attributes = True
