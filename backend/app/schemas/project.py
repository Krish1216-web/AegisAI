import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    status: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    owner_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None
    member_count: int = 0
    resource_count: int = 0

    class Config:
        from_attributes = True

class ProjectListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    projects: List[ProjectResponse] = Field(default_factory=list)

class ProjectMemberBase(BaseModel):
    user_id: uuid.UUID
    role: str = Field("viewer", description="owner, editor, viewer")

class ProjectMemberCreate(ProjectMemberBase):
    pass

class ProjectMemberUpdate(BaseModel):
    role: str = Field(..., description="owner, editor, viewer")

class ProjectMemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    email: str
    role: str
    status: str
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

class ProjectMemberListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    members: List[ProjectMemberResponse] = Field(default_factory=list)

class ProjectOwnershipTransferRequest(BaseModel):
    target_user_id: uuid.UUID = Field(..., description="Target project member user ID")

class ProjectResourceLinkRequest(BaseModel):
    resource_type: str = Field(..., description="document, workflow, agent")
    resource_id: str = Field(..., description="Target resource unique identifier")

class ProjectResourceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workspace_id: uuid.UUID
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime.datetime

class ProjectResourceListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    resources: List[ProjectResourceResponse] = Field(default_factory=list)
