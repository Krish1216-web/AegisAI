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
    TeamMemberListResponse,
    TeamOwnershipTransferRequest,
    EligibleMemberListResponse,
    TeamInvitationCreate,
    TeamInvitationResponse,
    TeamInvitationListResponse
)

router = APIRouter(prefix="", tags=["Team Collaboration & Membership"])

def _get_active_workspace_id(user: User, db: Session) -> uuid.UUID:
    if hasattr(user, "workspace_id") and user.workspace_id:
        return user.workspace_id

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

@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
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

@router.get("/teams", response_model=TeamListResponse)
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

@router.get("/teams/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.get_team(workspace_id=workspace_id, team_id=team_id)

@router.put("/teams/{team_id}", response_model=TeamResponse)
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

@router.post("/teams/{team_id}/archive", response_model=TeamResponse)
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

@router.post("/teams/{team_id}/restore", response_model=TeamResponse)
def restore_team(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    return service.restore_team(
        workspace_id=workspace_id,
        team_id=team_id,
        actor_id=current_user.id
    )

@router.post("/teams/{team_id}/transfer-ownership", response_model=TeamResponse)
def transfer_ownership(
    team_id: uuid.UUID,
    payload: TeamOwnershipTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    return service.transfer_ownership(
        workspace_id=workspace_id,
        team_id=team_id,
        target_user_id=payload.target_user_id,
        actor_id=current_user.id
    )

@router.get("/teams/{team_id}/eligible-members", response_model=EligibleMemberListResponse)
def get_eligible_members(
    team_id: uuid.UUID,
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.get_eligible_members(
        workspace_id=workspace_id,
        team_id=team_id,
        search=search,
        limit=limit
    )

@router.get("/teams/{team_id}/members", response_model=TeamMemberListResponse)
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

@router.post("/teams/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
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

@router.delete("/teams/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
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

@router.post("/teams/{team_id}/invitations", response_model=TeamInvitationResponse, status_code=status.HTTP_201_CREATED)
def create_team_invitation(
    team_id: uuid.UUID,
    payload: TeamInvitationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    _assert_can_manage_team(workspace_id, current_user, team_id, db)
    service = TeamService(db)
    return service.create_invitation(
        workspace_id=workspace_id,
        team_id=team_id,
        invited_user_id=payload.invited_user_id,
        invited_email=payload.invited_email,
        role=payload.role,
        invited_by=current_user.id
    )

@router.get("/teams/{team_id}/invitations", response_model=TeamInvitationListResponse)
def list_team_invitations(
    team_id: uuid.UUID,
    status: Optional[str] = Query("pending"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    return service.list_invitations(
        workspace_id=workspace_id,
        team_id=team_id,
        status_filter=status,
        page=page,
        page_size=page_size
    )

@router.post("/team-invitations/{invitation_id}/accept", response_model=TeamMemberResponse)
def accept_team_invitation(
    invitation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TeamService(db)
    return service.accept_invitation(
        invitation_id=invitation_id,
        user_id=current_user.id
    )

@router.post("/team-invitations/{invitation_id}/revoke", status_code=status.HTTP_200_OK)
def revoke_team_invitation(
    invitation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = _get_active_workspace_id(current_user, db)
    service = TeamService(db)
    service.revoke_invitation(
        workspace_id=workspace_id,
        invitation_id=invitation_id,
        actor_id=current_user.id
    )
    return {"message": "Invitation revoked successfully."}
