from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
from typing import Optional

from app.database.session import get_db
from app.schemas.workspace import (
    WorkspaceResponse, 
    WorkspaceCreate, 
    WorkspaceUpdate, 
    WorkspaceMemberResponse, 
    WorkspaceMemberCreate,
    WorkspaceMemberDetailResponse,
    WorkspaceMemberListResponse,
    WorkspaceMemberRoleUpdate,
    WorkspaceOwnershipTransferRequest,
    EffectivePermissionsResponse
)
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.workspace import WorkspaceService
from app.services.authorization import AuthorizationService

router = APIRouter(prefix="/workspaces", tags=["Workspace Management & Roles"])

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws_service = WorkspaceService(db)
    return ws_service.create_workspace(payload.name, payload.organization_id, current_user.id)

@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    if current_member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires owner or admin permissions to modify workspace details."
        )
    ws_service = WorkspaceService(db)
    return ws_service.update_workspace(workspace_id, payload.name)

@router.get("/{workspace_id}/members", response_model=WorkspaceMemberListResponse)
def list_workspace_members(
    workspace_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    ws_service = WorkspaceService(db)
    return ws_service.list_workspace_members(
        ws_id=workspace_id,
        page=page,
        page_size=page_size,
        search=search
    )

@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceMemberCreate,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    if current_member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires owner or admin permissions to manage membership roles."
        )
    ws_service = WorkspaceService(db)
    return ws_service.add_workspace_member(workspace_id, payload.user_id, payload.role)

@router.put("/{workspace_id}/members/{user_id}/role", response_model=WorkspaceMemberDetailResponse)
def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: WorkspaceMemberRoleUpdate,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws_service = WorkspaceService(db)
    return ws_service.update_workspace_member_role(
        ws_id=workspace_id,
        target_user_id=user_id,
        new_role=payload.role,
        actor_id=current_user.id
    )

@router.post("/{workspace_id}/transfer-ownership", response_model=WorkspaceMemberDetailResponse)
def transfer_workspace_ownership(
    workspace_id: uuid.UUID,
    payload: WorkspaceOwnershipTransferRequest,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_member.role != "owner" and (not current_user.role or current_user.role.name != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can transfer workspace ownership."
        )
    ws_service = WorkspaceService(db)
    return ws_service.transfer_workspace_ownership(
        ws_id=workspace_id,
        target_user_id=payload.target_user_id,
        actor_id=current_user.id
    )

@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    if current_member.role not in ["owner", "admin"] and current_member.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden."
        )
    ws_service = WorkspaceService(db)
    ws_service.remove_workspace_member(workspace_id, user_id)

@router.get("/{workspace_id}/effective-permissions", response_model=EffectivePermissionsResponse)
def get_effective_permissions(
    workspace_id: uuid.UUID,
    team_id: Optional[uuid.UUID] = Query(None),
    current_member: WorkspaceMember = Depends(get_workspace_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    auth_service = AuthorizationService(db)
    perms = auth_service.get_effective_permissions(
        user_id=current_user.id,
        workspace_id=workspace_id,
        team_id=team_id
    )

    team_role = None
    if team_id:
        from app.models.team import TeamMembership
        tm = db.query(TeamMembership).filter(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == current_user.id,
            TeamMembership.status == "active"
        ).first()
        if tm:
            team_role = tm.role

    return EffectivePermissionsResponse(
        user_id=current_user.id,
        workspace_id=workspace_id,
        team_id=team_id,
        workspace_role=current_member.role,
        team_role=team_role,
        permissions=sorted(list(perms))
    )
