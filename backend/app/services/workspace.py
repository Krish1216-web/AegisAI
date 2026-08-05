from sqlalchemy.orm import Session
from loguru import logger
import uuid
from typing import List, Optional, Any

from app.repositories.workspace import OrganizationRepository, WorkspaceRepository, WorkspaceMemberRepository
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.core.exceptions import AegisBaseException

class WorkspaceService:
    """
    Coordinates CRUD execution on Organizations, Workspaces, and members.
    """
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.member_repo = WorkspaceMemberRepository(db)

    # ORGANIZATION CRUD
    def create_organization(self, name: str, owner_id: uuid.UUID) -> Organization:
        org = Organization(name=name, created_by=owner_id)
        created_org = self.org_repo.create(org)
        logger.info(f"Organization created: {name} by owner {owner_id}")
        return created_org

    def update_organization(self, org_id: uuid.UUID, name: str) -> Organization:
        org = self.org_repo.get_by_id(org_id)
        if not org:
            raise AegisBaseException("Organization not found.", code="ORG_NOT_FOUND")
        org.name = name
        return self.org_repo.update(org)

    # WORKSPACE CRUD
    def create_workspace(self, name: str, org_id: uuid.UUID, user_id: uuid.UUID) -> Workspace:
        workspace = Workspace(name=name, organization_id=org_id, created_by=user_id)
        created_ws = self.workspace_repo.create(workspace)
        
        # Add creator as Workspace Owner
        member = WorkspaceMember(workspace_id=created_ws.id, user_id=user_id, role="owner")
        self.member_repo.create(member)
        
        logger.info(f"Workspace {name} created inside org {org_id} by user {user_id}")
        return created_ws

    def update_workspace(self, ws_id: uuid.UUID, name: str) -> Workspace:
        ws = self.workspace_repo.get_by_id(ws_id)
        if not ws:
            raise AegisBaseException("Workspace not found.", code="WORKSPACE_NOT_FOUND")
        ws.name = name
        return self.workspace_repo.update(ws)

    # MEMBER MANAGEMENT
    def add_workspace_member(self, ws_id: uuid.UUID, user_id: uuid.UUID, role: str = "member") -> WorkspaceMember:
        # Check if already a member
        existing = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if existing:
            raise AegisBaseException("User is already a member of this workspace.", code="DUPLICATE_MEMBER")
            
        member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role=role)
        return self.member_repo.create(member)

    def remove_workspace_member(self, ws_id: uuid.UUID, user_id: uuid.UUID):
        member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not member:
            raise AegisBaseException("Workspace member relation not found.", code="MEMBER_NOT_FOUND")
            
        self.db.delete(member)
        self.db.commit()
        logger.info(f"User {user_id} removed from workspace {ws_id}")
