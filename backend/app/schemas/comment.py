import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)
    project_id: Optional[uuid.UUID] = None
    resource_type: Optional[str] = None # document, workflow, agent
    resource_id: Optional[str] = None
    parent_comment_id: Optional[uuid.UUID] = None

class CommentUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)

class CommentMentionResponse(BaseModel):
    user_id: uuid.UUID
    username: str

class CommentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    author_name: str
    project_id: Optional[uuid.UUID] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    parent_comment_id: Optional[uuid.UUID] = None
    body: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    edited_at: Optional[datetime.datetime] = None
    deleted_at: Optional[datetime.datetime] = None
    reply_count: int = 0
    mentions: List[CommentMentionResponse] = Field(default_factory=list)

class CommentListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    comments: List[CommentResponse] = Field(default_factory=list)

class MentionableUserResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    email: str

class ActivityItemResponse(BaseModel):
    id: uuid.UUID
    activity_type: str
    description: str
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    created_at: datetime.datetime

class ActivityListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    activities: List[ActivityItemResponse] = Field(default_factory=list)
