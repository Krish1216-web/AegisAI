from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
from typing import Optional, List

from app.database.session import get_db
from app.schemas.comment import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentListResponse,
    MentionableUserResponse,
    ActivityListResponse
)
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.comment import CommentService

router = APIRouter(tags=["Comments & Collaboration Activity"])

@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    return service.create_comment(
        workspace_id=workspace_member.workspace_id,
        author_id=current_user.id,
        body=payload.body,
        project_id=payload.project_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        parent_comment_id=payload.parent_comment_id
    )

@router.get("/comments", response_model=CommentListResponse)
def list_comments(
    project_id: Optional[uuid.UUID] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    parent_comment_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    return service.list_comments(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        parent_comment_id=parent_comment_id,
        page=page,
        page_size=page_size
    )

@router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdate,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    return service.update_comment(
        workspace_id=workspace_member.workspace_id,
        comment_id=comment_id,
        body=payload.body,
        actor_id=current_user.id
    )

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    service.delete_comment(
        workspace_id=workspace_member.workspace_id,
        comment_id=comment_id,
        actor_id=current_user.id
    )

@router.get("/projects/{project_id}/comments", response_model=CommentListResponse)
def list_project_comments(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    return service.list_comments(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        page=page,
        page_size=page_size
    )

@router.get("/projects/{project_id}/mentionable-users", response_model=List[MentionableUserResponse])
def list_project_mentionable_users(
    project_id: uuid.UUID,
    search: Optional[str] = Query(None),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    return service.list_mentionable_users(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        search=search
    )

@router.get("/projects/{project_id}/activity", response_model=ActivityListResponse)
def list_project_activity(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    return service.list_activity(
        workspace_id=workspace_member.workspace_id,
        page=page,
        page_size=page_size
    )
