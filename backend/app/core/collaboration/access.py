import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.project import Project, ProjectMembership, ProjectResource
from app.services.authorization import AuthorizationService

class CollaborationResourceAccessService:
    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthorizationService(db)

    def check_access(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        team_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        required_permission: Optional[str] = None
    ) -> bool:
        # Step 1: Workspace membership
        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member:
            return False

        # Step 2: Permission check
        if required_permission:
            if not self.auth_service.authorize(
                user_id=user_id,
                workspace_id=workspace_id,
                permission=required_permission,
                team_id=team_id,
                project_id=project_id,
                resource_id=resource_id
            ):
                return False

        # Step 3: Team check
        if team_id:
            team = self.db.query(Team).filter(
                Team.id == team_id,
                Team.workspace_id == workspace_id,
                Team.status == "active"
            ).first()
            if not team:
                return False
            team_member = self.db.query(TeamMembership).filter(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
                TeamMembership.status == "active"
            ).first()
            if not team_member:
                return False

        # Step 4: Project check
        if project_id:
            project = self.db.query(Project).filter(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
                Project.status == "active"
            ).first()
            if not project:
                return False
            # Check if linked to project
            is_linked = self.db.query(ProjectResource).filter(
                ProjectResource.project_id == project_id,
                ProjectResource.resource_type == resource_type,
                ProjectResource.resource_id == resource_id
            ).first()
            if not is_linked:
                return False

        return True
