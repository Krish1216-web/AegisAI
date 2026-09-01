import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Set, Dict

class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    organization_id: uuid.UUID

class WorkspaceUpdate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkspaceMemberBase(BaseModel):
    user_id: uuid.UUID
    role: str = "member"

class WorkspaceMemberCreate(WorkspaceMemberBase):
    pass

class WorkspaceMemberRoleUpdate(BaseModel):
    role: str = Field(..., description="New role: owner, admin, member, viewer")

class WorkspaceOwnershipTransferRequest(BaseModel):
    target_user_id: uuid.UUID = Field(..., description="Target user ID to become the new workspace owner")

class WorkspaceMemberResponse(WorkspaceMemberBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkspaceMemberDetailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    email: str
    role: str
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

class WorkspaceMemberListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    members: List[WorkspaceMemberDetailResponse] = Field(default_factory=list)

class EffectivePermissionsResponse(BaseModel):
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    workspace_role: Optional[str] = None
    team_role: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

class PermissionRegistryResponse(BaseModel):
    permissions: List[str] = Field(default_factory=list)
    workspace_roles: Dict[str, List[str]] = Field(default_factory=dict)
    team_roles: Dict[str, List[str]] = Field(default_factory=dict)
