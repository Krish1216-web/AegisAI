import uuid
from typing import Set, Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.project import Project, ProjectMembership
from app.core.auth.permissions import (
    Permissions,
    ALL_PERMISSIONS,
    WORKSPACE_ROLE_PERMISSIONS,
    TEAM_ROLE_OVERLAY,
    PROJECT_ROLE_OVERLAY
)

class AuthorizationService:
    def __init__(self, db: Session):
        self.db = db

    def get_effective_permissions(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        team_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None
    ) -> Set[str]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or user.is_deleted:
            return set()

        if user.role and user.role.name.lower() in ["admin", "super admin"]:
            return set(ALL_PERMISSIONS)

        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member:
            return set()

        ws_role = ws_member.role.lower()
        effective_perms = set(WORKSPACE_ROLE_PERMISSIONS.get(ws_role, set()))

        # Team Role Overlay
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
                    effective_perms.update(TEAM_ROLE_OVERLAY.get(team_role, set()))

        # Project Role Overlay
        if project_id:
            project = self.db.query(Project).filter(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
                Project.status == "active"
            ).first()
            if project:
                proj_member = self.db.query(ProjectMembership).filter(
                    ProjectMembership.project_id == project.id,
                    ProjectMembership.user_id == user_id,
                    ProjectMembership.status == "active"
                ).first()
                if proj_member:
                    proj_role = proj_member.role.lower()
                    effective_perms.update(PROJECT_ROLE_OVERLAY.get(proj_role, set()))

        return effective_perms

    def authorize(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        permission: str,
        team_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        effective_perms = self.get_effective_permissions(
            user_id=user_id,
            workspace_id=workspace_id,
            team_id=team_id,
            project_id=project_id
        )
        return permission in effective_perms

    def assert_authorized(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        permission: str,
        team_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None
    ) -> None:
        if not self.authorize(user_id, workspace_id, permission, team_id, project_id, resource_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action forbidden. Requires permission: '{permission}'."
            )

    def assert_workspace_ownership(
        self,
        resource_workspace_id: uuid.UUID,
        request_workspace_id: uuid.UUID
    ) -> None:
        """
        Enforces that a resource's workspace matches the request context workspace.
        """
        if resource_workspace_id != request_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource belongs to another workspace. Access denied."
            )

    def create_security_context(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        team_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        trust_level: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        from app.core.platform.security import SecurityContext, TrustLevel
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or not found."
            )
        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member and not (user.role and user.role.name.lower() in ["admin", "super admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of the target workspace."
            )
        role = ws_member.role.lower() if ws_member else (user.role.name.lower() if user.role else "viewer")
        effective_perms = self.get_effective_permissions(
            user_id=user_id,
            workspace_id=workspace_id,
            team_id=team_id,
            project_id=project_id
        )
        return SecurityContext(
            user_id=user_id,
            workspace_id=workspace_id,
            user_role=role,
            permissions=effective_perms,
            trust_level=TrustLevel(trust_level) if isinstance(trust_level, str) else trust_level,
            tenant_boundary_enforced=True,
            metadata=metadata or {}
        )
