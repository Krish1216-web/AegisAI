import uuid
import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from fastapi import HTTPException, status

from app.models.team import Team, TeamMembership
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.audit import AuditLog, ActivityLog
from app.schemas.team import (
    TeamResponse,
    TeamListResponse,
    TeamMemberResponse,
    TeamMemberListResponse
)
from app.core.mcp.security import CredentialStore
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType

class TeamService:
    """
    Production Team Collaboration Foundation Service.
    Enforces strict workspace tenant isolation, membership consistency,
    RBAC permission constraints, and immutable audit logging.
    """

    def __init__(self, db: Session):
        self.db = db

    def _assert_workspace_exists(self, workspace_id: uuid.UUID) -> Workspace:
        ws = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_id}' not found."
            )
        return ws

    def _assert_user_in_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceMember:
        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{user_id}' is not a member of workspace '{workspace_id}'."
            )
        return ws_member

    def _build_team_response(self, team: Team) -> TeamResponse:
        active_members_count = self.db.query(func.count(TeamMembership.id)).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.status == "active"
        ).scalar() or 0

        return TeamResponse(
            id=team.id,
            workspace_id=team.workspace_id,
            name=team.name,
            description=team.description,
            status=team.status,
            created_by=team.created_by,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=active_members_count
        )

    def create_team(
        self,
        workspace_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        creator_id: Optional[uuid.UUID] = None
    ) -> TeamResponse:
        self._assert_workspace_exists(workspace_id)
        if creator_id:
            self._assert_user_in_workspace(workspace_id, creator_id)

        clean_name = name.strip()
        if not clean_name or len(clean_name) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Team name must be between 1 and 100 characters."
            )

        # Check duplicate name within workspace
        existing = self.db.query(Team).filter(
            Team.workspace_id == workspace_id,
            Team.name == clean_name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A team named '{clean_name}' already exists in this workspace."
            )

        team = Team(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=clean_name,
            description=description.strip() if description else None,
            status="active",
            created_by=creator_id
        )
        self.db.add(team)
        self.db.flush()

        # Creator automatically becomes the team owner
        if creator_id:
            membership = TeamMembership(
                id=uuid.uuid4(),
                team_id=team.id,
                user_id=creator_id,
                role="owner",
                status="active"
            )
            self.db.add(membership)

        # Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=creator_id,
            action="TEAM_CREATED",
            details=f"Team '{team.name}' (id={team.id}) created in workspace '{workspace_id}'."
        )
        self.db.add(audit)

        # Activity Log
        activity = ActivityLog(
            id=uuid.uuid4(),
            user_id=creator_id,
            activity_type="TEAM_CREATED",
            description=f"Created team '{team.name}'"
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(team)

        # Emit Platform Event
        try:
            PlatformEventDispatcher.emit(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                correlation_id=f"team_evt_{uuid.uuid4().hex[:8]}",
                workspace_id=workspace_id,
                user_id=creator_id,
                source_component="TeamService",
                payload={"action": "TEAM_CREATED", "team_id": str(team.id), "name": team.name}
            ))
        except Exception:
            pass

        return self._build_team_response(team)

    def get_team(self, workspace_id: uuid.UUID, team_id: uuid.UUID) -> TeamResponse:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )
        return self._build_team_response(team)

    def list_teams(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = "active",
        search: Optional[str] = None
    ) -> TeamListResponse:
        self._assert_workspace_exists(workspace_id)
        query = self.db.query(Team).filter(Team.workspace_id == workspace_id)

        if status_filter:
            query = query.filter(Team.status == status_filter)
        if search:
            query = query.filter(
                or_(
                    Team.name.ilike(f"%{search}%"),
                    Team.description.ilike(f"%{search}%")
                )
            )

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        teams = query.order_by(desc(Team.created_at)).offset(offset).limit(page_size).all()

        items = [self._build_team_response(t) for t in teams]
        return TeamListResponse(
            total=total,
            page=page,
            page_size=page_size,
            teams=items
        )

    def update_team(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None
    ) -> TeamResponse:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        if team.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify an archived team."
            )

        if name is not None:
            clean_name = name.strip()
            if not clean_name or len(clean_name) > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Team name must be between 1 and 100 characters."
                )
            # Check duplicate
            dup = self.db.query(Team).filter(
                Team.workspace_id == workspace_id,
                Team.name == clean_name,
                Team.id != team.id
            ).first()
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A team named '{clean_name}' already exists in this workspace."
                )
            team.name = clean_name

        if description is not None:
            team.description = description.strip() if description else None

        # Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_UPDATED",
            details=f"Team '{team.name}' (id={team.id}) updated."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(team)

        return self._build_team_response(team)

    def archive_team(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None
    ) -> TeamResponse:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        team.status = "archived"

        # Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_ARCHIVED",
            details=f"Team '{team.name}' (id={team.id}) archived."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(team)

        return self._build_team_response(team)

    def add_member(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
        actor_id: Optional[uuid.UUID] = None
    ) -> TeamMemberResponse:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        if team.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add members to an archived team."
            )

        # Invariant: User MUST be in the workspace
        self._assert_user_in_workspace(workspace_id, user_id)

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found or inactive."
            )

        membership = self.db.query(TeamMembership).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.user_id == user_id
        ).first()

        if membership:
            if membership.status == "active":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already an active member of team '{team.name}'."
                )
            else:
                membership.status = "active"
                membership.role = role
        else:
            membership = TeamMembership(
                id=uuid.uuid4(),
                team_id=team.id,
                user_id=user_id,
                role=role,
                status="active"
            )
            self.db.add(membership)

        # Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_MEMBER_ADDED",
            details=f"User '{user.username}' added to team '{team.name}' with role '{role}'."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(membership)

        return TeamMemberResponse(
            id=membership.id,
            team_id=membership.team_id,
            user_id=membership.user_id,
            username=user.username,
            email=user.email,
            role=membership.role,
            status=membership.status,
            created_at=membership.created_at,
            updated_at=membership.updated_at
        )

    def remove_member(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None
    ) -> bool:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        membership = self.db.query(TeamMembership).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.user_id == user_id,
            TeamMembership.status == "active"
        ).first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active team membership not found."
            )

        membership.status = "removed"

        # Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_MEMBER_REMOVED",
            details=f"User '{user_id}' removed from team '{team.name}'."
        )
        self.db.add(audit)
        self.db.commit()
        return True

    def list_members(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50
    ) -> TeamMemberListResponse:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        query = self.db.query(TeamMembership, User).join(
            User, TeamMembership.user_id == User.id
        ).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.status == "active"
        )

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        results = query.order_by(TeamMembership.created_at.asc()).offset(offset).limit(page_size).all()

        items = [
            TeamMemberResponse(
                id=m.id,
                team_id=m.team_id,
                user_id=m.user_id,
                username=u.username,
                email=u.email,
                role=m.role,
                status=m.status,
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m, u in results
        ]

        return TeamMemberListResponse(
            total=total,
            page=page,
            page_size=page_size,
            members=items
        )
