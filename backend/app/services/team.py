import uuid
import hashlib
import secrets
import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from fastapi import HTTPException, status

from app.models.team import Team, TeamMembership, TeamInvitation
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.audit import AuditLog, ActivityLog
from app.schemas.team import (
    TeamResponse,
    TeamListResponse,
    TeamMemberResponse,
    TeamMemberListResponse,
    EligibleMemberResponse,
    EligibleMemberListResponse,
    TeamInvitationResponse,
    TeamInvitationListResponse
)
from app.core.mcp.security import CredentialStore
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType
from app.core.collaboration.realtime import RealtimeConnectionManager

class TeamService:
    """
    Production Team Collaboration Foundation & Advanced Membership Service (Phase 9.2).
    Enforces strict workspace tenant isolation, membership consistency,
    atomic ownership transfer, cryptographic invitation workflows,
    and sanitized audit logging.
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

        # Resolve owner
        owner_membership = self.db.query(TeamMembership, User).join(
            User, TeamMembership.user_id == User.id
        ).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.role == "owner",
            TeamMembership.status == "active"
        ).first()

        owner_id = owner_membership[0].user_id if owner_membership else None
        owner_name = owner_membership[1].username if owner_membership else None

        return TeamResponse(
            id=team.id,
            workspace_id=team.workspace_id,
            name=team.name,
            description=team.description,
            status=team.status,
            created_by=team.created_by,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=active_members_count,
            owner_id=owner_id,
            owner_name=owner_name
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

        if creator_id:
            membership = TeamMembership(
                id=uuid.uuid4(),
                team_id=team.id,
                user_id=creator_id,
                role="owner",
                status="active"
            )
            self.db.add(membership)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=creator_id,
            action="TEAM_CREATED",
            details=f"Team '{team.name}' (id={team.id}) created in workspace '{workspace_id}'."
        )
        self.db.add(audit)

        activity = ActivityLog(
            id=uuid.uuid4(),
            user_id=creator_id,
            activity_type="TEAM_CREATED",
            description=f"Created team '{team.name}'"
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(team)

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

    def restore_team(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None
    ) -> TeamResponse:
        """
        Restores an archived team to active status.
        Ensures name uniqueness against current active teams.
        """
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        if team.status == "active":
            return self._build_team_response(team)

        # Check for active name collision
        collision = self.db.query(Team).filter(
            Team.workspace_id == workspace_id,
            Team.name == team.name,
            Team.status == "active",
            Team.id != team.id
        ).first()
        if collision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot restore: an active team named '{team.name}' already exists."
            )

        team.status = "active"

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_RESTORED",
            details=f"Team '{team.name}' (id={team.id}) restored to active status."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(team)

        return self._build_team_response(team)

    def transfer_ownership(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        target_user_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None
    ) -> TeamResponse:
        """
        Atomically transfers team ownership to target user.
        Previous owner becomes 'member', target user becomes 'owner'.
        Target user must be an active member of the team.
        """
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
                detail="Cannot transfer ownership of an archived team."
            )

        # Check target is active member of team
        target_membership = self.db.query(TeamMembership).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.user_id == target_user_id,
            TeamMembership.status == "active"
        ).first()
        if not target_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user must be an active member of the team to receive ownership."
            )

        if target_membership.role == "owner":
            return self._build_team_response(team)

        # Demote existing active owner(s) to 'member'
        existing_owners = self.db.query(TeamMembership).filter(
            TeamMembership.team_id == team.id,
            TeamMembership.role == "owner",
            TeamMembership.status == "active"
        ).all()
        for om in existing_owners:
            om.role = "member"

        # Promote target to 'owner'
        target_membership.role = "owner"

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_OWNER_TRANSFERRED",
            details=f"Team '{team.name}' (id={team.id}) ownership transferred to user '{target_user_id}'."
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

        action_name = "TEAM_MEMBER_ADDED"
        if membership:
            if membership.status == "active":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already an active member of team '{team.name}'."
                )
            else:
                membership.status = "active"
                membership.role = role
                action_name = "TEAM_MEMBERSHIP_REACTIVATED"
        else:
            membership = TeamMembership(
                id=uuid.uuid4(),
                team_id=team.id,
                user_id=user_id,
                role=role,
                status="active"
            )
            self.db.add(membership)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action=action_name,
            details=f"User '{user.username}' added/reactivated in team '{team.name}' with role '{role}'."
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

        # Owner Protection Rule: Cannot remove the sole active owner
        if membership.role == "owner":
            active_owners_count = self.db.query(func.count(TeamMembership.id)).filter(
                TeamMembership.team_id == team.id,
                TeamMembership.role == "owner",
                TeamMembership.status == "active"
            ).scalar() or 0
            if active_owners_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the sole team owner. Transfer ownership before removal."
                )

        membership.status = "removed"

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_MEMBER_REMOVED",
            details=f"User '{user_id}' removed from team '{team.name}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(team.workspace_id, user_id, f"team:{team_id}")
        except Exception:
            pass
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

    def get_eligible_members(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        search: Optional[str] = None,
        limit: int = 50
    ) -> EligibleMemberListResponse:
        """
        Discovers workspace members who are NOT currently active in the team.
        Returns sanitized user summaries for member invitation.
        """
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        # Get existing active team member IDs
        active_team_user_ids = [
            r[0] for r in self.db.query(TeamMembership.user_id).filter(
                TeamMembership.team_id == team.id,
                TeamMembership.status == "active"
            ).all()
        ]

        query = self.db.query(WorkspaceMember, User).join(
            User, WorkspaceMember.user_id == User.id
        ).filter(
            WorkspaceMember.workspace_id == workspace_id,
            User.is_active == True,
            User.is_deleted == False
        )

        if active_team_user_ids:
            query = query.filter(~WorkspaceMember.user_id.in_(active_team_user_ids))

        if search:
            query = query.filter(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

        total = query.count()
        results = query.order_by(User.username.asc()).limit(limit).all()

        items = [
            EligibleMemberResponse(
                user_id=u.id,
                username=u.username,
                email=u.email,
                workspace_role=wm.role
            )
            for wm, u in results
        ]

        return EligibleMemberListResponse(
            total=total,
            members=items
        )

    def create_invitation(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        invited_user_id: Optional[uuid.UUID] = None,
        invited_email: Optional[str] = None,
        role: str = "member",
        invited_by: Optional[uuid.UUID] = None,
        expires_days: int = 7
    ) -> TeamInvitationResponse:
        """
        Creates a secure, token-hashed team invitation.
        """
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
                detail="Cannot invite members to an archived team."
            )

        if not invited_user_id and not invited_email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must specify either invited_user_id or invited_email."
            )

        target_user = None
        if invited_user_id:
            self._assert_user_in_workspace(workspace_id, invited_user_id)
            target_user = self.db.query(User).filter(User.id == invited_user_id).first()
            if not target_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")
            invited_email = target_user.email

            # Check existing active membership
            active_m = self.db.query(TeamMembership).filter(
                TeamMembership.team_id == team.id,
                TeamMembership.user_id == invited_user_id,
                TeamMembership.status == "active"
            ).first()
            if active_m:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already an active member of team '{team.name}'."
                )

        # Check existing pending invitation
        pending_q = self.db.query(TeamInvitation).filter(
            TeamInvitation.team_id == team.id,
            TeamInvitation.status == "pending"
        )
        if invited_user_id:
            pending_q = pending_q.filter(TeamInvitation.invited_user_id == invited_user_id)
        elif invited_email:
            pending_q = pending_q.filter(TeamInvitation.invited_email == invited_email)
        if pending_q.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invitation already exists for this user/email."
            )

        # Generate cryptographically secure token & SHA-256 hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=expires_days)

        invitation = TeamInvitation(
            id=uuid.uuid4(),
            team_id=team.id,
            workspace_id=workspace_id,
            invited_user_id=invited_user_id,
            invited_email=invited_email,
            invited_by=invited_by,
            token_hash=token_hash,
            role=role,
            status="pending",
            expires_at=expires_at
        )
        self.db.add(invitation)

        # Audit Log (never log raw token!)
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=invited_by,
            action="TEAM_INVITATION_CREATED",
            details=f"Invitation created for '{invited_email}' to team '{team.name}' with role '{role}'."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(invitation)

        return TeamInvitationResponse(
            id=invitation.id,
            team_id=invitation.team_id,
            workspace_id=invitation.workspace_id,
            invited_user_id=invitation.invited_user_id,
            invited_email=invitation.invited_email,
            invited_by=invitation.invited_by,
            role=invitation.role,
            status=invitation.status,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            created_at=invitation.created_at
        )

    def list_invitations(
        self,
        workspace_id: uuid.UUID,
        team_id: uuid.UUID,
        status_filter: Optional[str] = "pending",
        page: int = 1,
        page_size: int = 20
    ) -> TeamInvitationListResponse:
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.workspace_id == workspace_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_id}' not found in workspace '{workspace_id}'."
            )

        query = self.db.query(TeamInvitation).filter(
            TeamInvitation.team_id == team.id,
            TeamInvitation.workspace_id == workspace_id
        )
        if status_filter:
            query = query.filter(TeamInvitation.status == status_filter)

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        invitations = query.order_by(desc(TeamInvitation.created_at)).offset(offset).limit(page_size).all()

        items = [
            TeamInvitationResponse(
                id=inv.id,
                team_id=inv.team_id,
                workspace_id=inv.workspace_id,
                invited_user_id=inv.invited_user_id,
                invited_email=inv.invited_email,
                invited_by=inv.invited_by,
                role=inv.role,
                status=inv.status,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
                created_at=inv.created_at
            )
            for inv in invitations
        ]

        return TeamInvitationListResponse(
            total=total,
            page=page,
            page_size=page_size,
            invitations=items
        )

    def accept_invitation(
        self,
        invitation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> TeamMemberResponse:
        """
        Accepts a team invitation for the authenticated user.
        Validates expiration, single-use, workspace membership, and creates/reactivates membership.
        """
        invitation = self.db.query(TeamInvitation).filter(
            TeamInvitation.id == invitation_id
        ).first()
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found."
            )

        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation cannot be accepted; status is '{invitation.status}'."
            )

        # Check expiration
        now = datetime.datetime.now(datetime.timezone.utc)
        if invitation.expires_at.tzinfo is None:
            expires_at = invitation.expires_at.replace(tzinfo=datetime.timezone.utc)
        else:
            expires_at = invitation.expires_at

        if now > expires_at:
            invitation.status = "expired"
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired."
            )

        # Verify target user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive.")

        if invitation.invited_user_id and invitation.invited_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different user."
            )

        if invitation.invited_email and user.email.lower() != invitation.invited_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User email does not match invitation recipient."
            )

        # Enforce workspace membership
        self._assert_user_in_workspace(invitation.workspace_id, user_id)

        # Mark invitation accepted
        invitation.status = "accepted"
        invitation.accepted_at = now
        invitation.invited_user_id = user_id

        # Add or reactivate team membership
        membership = self.db.query(TeamMembership).filter(
            TeamMembership.team_id == invitation.team_id,
            TeamMembership.user_id == user_id
        ).first()

        if membership:
            membership.status = "active"
            membership.role = invitation.role
        else:
            membership = TeamMembership(
                id=uuid.uuid4(),
                team_id=invitation.team_id,
                user_id=user_id,
                role=invitation.role,
                status="active"
            )
            self.db.add(membership)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action="TEAM_INVITATION_ACCEPTED",
            details=f"User '{user.username}' accepted invitation to team '{invitation.team_id}'."
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

    def revoke_invitation(
        self,
        workspace_id: uuid.UUID,
        invitation_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Revokes a pending invitation.
        """
        invitation = self.db.query(TeamInvitation).filter(
            TeamInvitation.id == invitation_id,
            TeamInvitation.workspace_id == workspace_id
        ).first()
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found."
            )

        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot revoke invitation with status '{invitation.status}'."
            )

        invitation.status = "revoked"

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="TEAM_INVITATION_REVOKED",
            details=f"Invitation '{invitation.id}' for team '{invitation.team_id}' revoked."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(team.workspace_id, user_id, f"team:{team_id}")
        except Exception:
            pass
        return True
