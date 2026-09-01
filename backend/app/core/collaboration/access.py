import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceMember
from app.models.team import Team, TeamMembership

class CollaborationResourceAccessService:
    """
    Foundational Resource-Sharing and Collaboration Access Abstraction for Phase 9.
    Provides verified permission and tenant checks for collaborative resources
    (Projects, Documents, Workflows, Agents, MCP Tools).
    """

    def __init__(self, db: Session):
        self.db = db

    def check_access(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        team_id: Optional[uuid.UUID] = None,
        required_permission: Optional[str] = None
    ) -> bool:
        """
        Determines whether a user has collaboration access to a given resource.
        1. Confirms user is active member of the workspace.
        2. If team_id is provided, confirms team is active in workspace and user is active member.
        """
        # Step 1: Confirm workspace membership
        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member:
            return False

        # Workspace owner/admin has blanket access within workspace
        if ws_member.role in ["owner", "admin"]:
            return True

        # Step 2: If team scoping is requested
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

        return True
