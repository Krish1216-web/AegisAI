from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
from typing import Optional

from app.database.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberUpdate,
    ProjectMemberResponse,
    ProjectMemberListResponse,
    ProjectOwnershipTransferRequest,
    ProjectResourceLinkRequest,
    ProjectResourceResponse,
    ProjectResourceListResponse
)
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["Shared Projects & Resources"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.create_project(
        workspace_id=workspace_member.workspace_id,
        name=payload.name,
        description=payload.description,
        creator_id=current_user.id
    )

@router.get("", response_model=ProjectListResponse)
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query("active"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.list_projects(
        workspace_id=workspace_member.workspace_id,
        actor_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status,
        search=search
    )

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.get_project(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        actor_id=current_user.id
    )

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.update_project(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        actor_id=current_user.id
    )

@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.archive_project(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        actor_id=current_user.id
    )

@router.post("/{project_id}/restore", response_model=ProjectResponse)
def restore_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.restore_project(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        actor_id=current_user.id
    )

@router.post("/{project_id}/transfer-ownership", response_model=ProjectResponse)
def transfer_project_ownership(
    project_id: uuid.UUID,
    payload: ProjectOwnershipTransferRequest,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.transfer_ownership(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        target_user_id=payload.target_user_id,
        actor_id=current_user.id
    )

# MEMBERS
@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
def list_project_members(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.list_members(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        page=page,
        page_size=page_size
    )

@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: uuid.UUID,
    payload: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.add_member(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        user_id=payload.user_id,
        role=payload.role,
        actor_id=current_user.id
    )

@router.put("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_project_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.update_member_role(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        user_id=user_id,
        role=payload.role,
        actor_id=current_user.id
    )

@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    service.remove_member(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        user_id=user_id,
        actor_id=current_user.id
    )

# RESOURCES
@router.get("/{project_id}/resources", response_model=ProjectResourceListResponse)
def list_project_resources(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    resource_type: Optional[str] = Query(None),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.list_resources(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        page=page,
        page_size=page_size,
        resource_type=resource_type
    )

@router.post("/{project_id}/resources", response_model=ProjectResourceResponse, status_code=status.HTTP_201_CREATED)
def link_project_resource(
    project_id: uuid.UUID,
    payload: ProjectResourceLinkRequest,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    return service.link_resource(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        actor_id=current_user.id
    )

@router.delete("/{project_id}/resources/{resource_type}/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_project_resource(
    project_id: uuid.UUID,
    resource_type: str,
    resource_id: str,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    service.unlink_resource(
        workspace_id=workspace_member.workspace_id,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=current_user.id
    )
