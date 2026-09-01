from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from loguru import logger
import uuid
from typing import List, Optional, Any
from fastapi import HTTPException, status

from app.repositories.workspace import OrganizationRepository, WorkspaceRepository, WorkspaceMemberRepository
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.models.user import User
from app.models.audit import AuditLog, ActivityLog
from app.core.exceptions import AegisBaseException
from app.schemas.workspace import (
    WorkspaceMemberDetailResponse,
    WorkspaceMemberListResponse,
    WorkspaceResponse
)

class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.member_repo = WorkspaceMemberRepository(db)

    def create_organization(self, name: str, owner_id: uuid.UUID) -> Organization:
        org = Organization(name=name, created_by=owner_id)
        created_org = self.org_repo.create(org)
        logger.info(f"Organization created: {name} by owner {owner_id}")
        return created_org

    def update_organization(self, org_id: uuid.UUID, name: str) -> Organization:
        org = self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
        org.name = name
        return self.org_repo.update(org)

    def create_workspace(self, name: str, org_id: uuid.UUID, user_id: uuid.UUID) -> Workspace:
        workspace = Workspace(name=name, organization_id=org_id, created_by=user_id)
        created_ws = self.workspace_repo.create(workspace)
        
        member = WorkspaceMember(workspace_id=created_ws.id, user_id=user_id, role="owner")
        self.member_repo.create(member)
        
        logger.info(f"Workspace {name} created inside org {org_id} by user {user_id}")
        return created_ws

    def update_workspace(self, ws_id: uuid.UUID, name: str) -> Workspace:
        ws = self.workspace_repo.get_by_id(ws_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
        ws.name = name
        return self.workspace_repo.update(ws)

    def list_workspace_members(
        self,
        ws_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> WorkspaceMemberListResponse:
        query = self.db.query(WorkspaceMember, User).join(
            User, WorkspaceMember.user_id == User.id
        ).filter(
            WorkspaceMember.workspace_id == ws_id,
            User.is_active == True,
            User.is_deleted == False
        )

        if search:
            query = query.filter(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        results = query.order_by(WorkspaceMember.created_at.asc()).offset(offset).limit(page_size).all()

        items = [
            WorkspaceMemberDetailResponse(
                id=wm.id,
                workspace_id=wm.workspace_id,
                user_id=wm.user_id,
                username=u.username,
                email=u.email,
                role=wm.role,
                created_at=wm.created_at,
                updated_at=wm.updated_at
            )
            for wm, u in results
        ]

        return WorkspaceMemberListResponse(
            total=total,
            page=page,
            page_size=page_size,
            members=items
        )

    def add_workspace_member(self, ws_id: uuid.UUID, user_id: uuid.UUID, role: str = "member") -> WorkspaceMember:
        if role not in ["owner", "admin", "member", "viewer"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid role: '{role}'.")

        existing = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this workspace.")
            
        member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role=role)
        created = self.member_repo.create(member)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action="WORKSPACE_MEMBER_ADDED",
            details=f"User '{user_id}' added to workspace '{ws_id}' with role '{role}'."
        )
        self.db.add(audit)
        self.db.commit()
        return created

    def update_workspace_member_role(
        self,
        ws_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
        actor_id: Optional[uuid.UUID] = None
    ) -> WorkspaceMemberDetailResponse:
        if new_role not in ["owner", "admin", "member", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid workspace role '{new_role}'. Must be owner, admin, member, or viewer."
            )

        member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == target_user_id
        ).first()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found.")

        user = self.db.query(User).filter(User.id == target_user_id).first()
        old_role = member.role

        if actor_id:
            actor_member = self.db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.user_id == actor_id
            ).first()
            actor_user = self.db.query(User).filter(User.id == actor_id).first()
            is_sys_admin = actor_user and actor_user.role and actor_user.role.name == "admin"
            
            if not is_sys_admin:
                if not actor_member or actor_member.role not in ["owner", "admin"]:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires owner or admin permissions.")
                if actor_member.role == "admin":
                    if new_role == "owner" or old_role == "owner":
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Workspace admin cannot promote to or demote workspace owner."
                        )

        if old_role == "owner" and new_role != "owner":
            owner_count = self.db.query(func.count(WorkspaceMember.id)).filter(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.role == "owner"
            ).scalar() or 0
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the sole workspace owner. Use transfer ownership instead."
                )

        member.role = new_role

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="WORKSPACE_ROLE_CHANGED",
            details=f"User '{target_user_id}' workspace role changed from '{old_role}' to '{new_role}'."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(member)

        return WorkspaceMemberDetailResponse(
            id=member.id,
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            username=user.username if user else "user",
            email=user.email if user else "user@internal",
            role=member.role,
            created_at=member.created_at,
            updated_at=member.updated_at
        )

    def transfer_workspace_ownership(
        self,
        ws_id: uuid.UUID,
        target_user_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None
    ) -> WorkspaceMemberDetailResponse:
        target_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == target_user_id
        ).first()
        if not target_member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user is not a member of this workspace.")

        user = self.db.query(User).filter(User.id == target_user_id).first()

        existing_owners = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.role == "owner"
        ).all()
        for om in existing_owners:
            om.role = "admin"

        target_member.role = "owner"

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="WORKSPACE_OWNER_TRANSFERRED",
            details=f"Workspace '{ws_id}' ownership transferred to user '{target_user_id}'."
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(target_member)

        return WorkspaceMemberDetailResponse(
            id=target_member.id,
            workspace_id=target_member.workspace_id,
            user_id=target_member.user_id,
            username=user.username if user else "user",
            email=user.email if user else "user@internal",
            role=target_member.role,
            created_at=target_member.created_at,
            updated_at=target_member.updated_at
        )

    def remove_workspace_member(self, ws_id: uuid.UUID, user_id: uuid.UUID):
        member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member relation not found.")

        if member.role == "owner":
            owner_count = self.db.query(func.count(WorkspaceMember.id)).filter(
                WorkspaceMember.workspace_id == ws_id,
                WorkspaceMember.role == "owner"
            ).scalar() or 0
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the sole workspace owner. Transfer ownership before removal."
                )

        self.db.delete(member)
        self.db.commit()
        logger.info(f"User {user_id} removed from workspace {ws_id}")
