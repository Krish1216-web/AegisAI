import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.team import TeamService
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamListResponse,
    TeamMemberAdd,
    TeamMemberResponse,
    TeamMemberListResponse
)

router = APIRouter(prefix="/teams", tags=["Team Collaboration"])

def _get_active_workspace_id(user: User, db: Session) -> uuid.UUID:
    """
    Resolves the caller's active workspace ID authoritatively from server-side state.
    """
    # 1. Check user.workspace_id attribute if present
    if hasattr(user, "workspace_id") and user.workspace_id:
        return user.workspace_id

    # 2. Check first active workspace membership
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user.id
    ).first()
    if membership:
        return membership.workspace_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not have an active workspace assignment."
    )

def _assert_can_manage_team(
    workspace_id: uuid.UUID,
    user: User,
    team_id: Optional[uuid.UUID],
    db: Session
) -> None:
    """
    Verifies RBAC: system admin, workspace owner/admin, or team owner.
    """
    if user.role and user.role.name == "admin":
        return

    ws_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()

    if ws_member and ws_member.role in ["owner", "admin"]:
        return

    if team_id:
        from app.models.team import TeamMembership
        tm = db.query(TeamMembership).filter(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user.id,
            TeamMembership.role == "owner",
            TeamMembership.status == "active"
        ).first()
        if tm:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Action requires team manager or workspace administrator permissions."
    )

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.create_team(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        creator_id=current_user.id
    )

@router.get("", response_model=TeamListResponse)
def list_teams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query("active"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.list_teams(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        status_filter=status,
        search=search
    )

@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.get_team(workspace_id=workspace_id, team_id=team_id)

@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    return service.update_team(
        workspace_id=workspace_id,
        team_id=team_id,
        name=payload.name,
        description=payload.description,
        actor_id=current_user.id
    )

@router.post("/{team_id}/archive", response_model=TeamResponse)
def archive_team(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    return service.archive_team(
        workspace_id=workspace_id,
        team_id=team_id,
        actor_id=current_user.id
    )

@router.get("/{team_id}/members", response_model=TeamMemberListResponse)
def list_team_members(
    team_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.list_members(
        workspace_id=workspace_id,
        team_id=team_id,
        page=page,
        page_size=page_size
    )

@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: uuid.UUID,
    payload: TeamMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    return service.add_member(
        workspace_id=workspace_id,
        team_id=team_id,
        user_id=payload.user_id,
        role=payload.role,
        actor_id=current_user.id
    )

@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    service.remove_member(
        workspace_id=workspace_id,
        team_id=team_id,
        user_id=user_id,
        actor_id=current_user.id
    )
    return {"message": f"User '{user_id}' removed from team successfully."}
