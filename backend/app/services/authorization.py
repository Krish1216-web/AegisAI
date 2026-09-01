import uuid
from typing import Set, Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.team import Team, TeamMembership
from app.core.auth.permissions import (
    Permissions,
    ALL_PERMISSIONS,
    WORKSPACE_ROLE_PERMISSIONS,
    TEAM_ROLE_OVERLAY
)

class AuthorizationService:
    """
    Authoritative Central Authorization Engine for AegisAI (Phase 9.3).
    Unifies system-level, workspace-level, and team-level permission evaluation.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_effective_permissions(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        team_id: Optional[uuid.UUID] = None
    ) -> Set[str]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or user.is_deleted:
            return set()

        if user.role and user.role.name == "admin":
            return set(ALL_PERMISSIONS)

        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member:
            return set()

        ws_role = ws_member.role.lower()
        effective_perms = set(WORKSPACE_ROLE_PERMISSIONS.get(ws_role, set()))

        if team_id:
            team = self.db.query(Team).filter(
                Team.id == team_id,
                Team.workspace_id == workspace_id,
                Team.status == "active"
            ).first()
            if team:
                team_member = self.db.query(TeamMembership).filter(
                    TeamMembership.team_id == team.id,
                    TeamMembership.user_id == user_id,
                    TeamMembership.status == "active"
                ).first()
                if team_member:
                    team_role = team_member.role.lower()
                    team_perms = TEAM_ROLE_OVERLAY.get(team_role, set())
                    effective_perms.update(team_perms)

        return effective_perms

    def authorize(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        permission: str,
        team_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        effective_perms = self.get_effective_permissions(
            user_id=user_id,
            workspace_id=workspace_id,
            team_id=team_id
        )
        return permission in effective_perms

    def assert_authorized(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        permission: str,
        team_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None
    ) -> None:
        if not self.authorize(user_id, workspace_id, permission, team_id, resource_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action forbidden. Requires permission: '{permission}'."
            )
