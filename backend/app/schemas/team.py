import uuid
import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the team")
    description: Optional[str] = Field(None, max_length=500, description="Brief description of the team")

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated name of the team")
    description: Optional[str] = Field(None, max_length=500, description="Updated description of the team")

class TeamOwnershipTransferRequest(BaseModel):
    target_user_id: uuid.UUID = Field(..., description="User ID of the active team member to become the new owner")

class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    email: str
    role: str # owner, member
    status: str # active, removed
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

class TeamMemberListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    members: List[TeamMemberResponse] = Field(default_factory=list)

class TeamMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = Field(default="member", description="Role within the team: owner, member")

class TeamMemberRoleUpdate(BaseModel):
    role: str = Field(..., description="Role within the team: owner, member")

class TeamResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str # active, archived
    created_by: Optional[uuid.UUID] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    member_count: int = 0
    owner_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None

class TeamListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    teams: List[TeamResponse] = Field(default_factory=list)

class EligibleMemberResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    email: str
    workspace_role: str

class EligibleMemberListResponse(BaseModel):
    total: int
    members: List[EligibleMemberResponse] = Field(default_factory=list)

class TeamInvitationCreate(BaseModel):
    invited_user_id: Optional[uuid.UUID] = Field(None, description="Workspace user ID to invite")
    invited_email: Optional[str] = Field(None, description="Email address to invite")
    role: str = Field(default="member", description="Assigned role upon acceptance")

class TeamInvitationResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    workspace_id: uuid.UUID
    invited_user_id: Optional[uuid.UUID] = None
    invited_email: Optional[str] = None
    invited_by: Optional[uuid.UUID] = None
    role: str
    status: str # pending, accepted, expired, revoked
    expires_at: datetime.datetime
    accepted_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

class TeamInvitationListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    invitations: List[TeamInvitationResponse] = Field(default_factory=list)
