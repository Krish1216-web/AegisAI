import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException, status
from loguru import logger

from app.models.project import Project, ProjectMembership, ProjectResource
from app.models.workspace import WorkspaceMember
from app.models.user import User
from app.models.document import Document
from app.models.workflow import Workflow
from app.models.audit import AuditLog
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType
from app.core.collaboration.realtime import RealtimeConnectionManager
from app.schemas.project import (
    ProjectResponse,
    ProjectListResponse,
    ProjectMemberResponse,
    ProjectMemberListResponse,
    ProjectResourceResponse,
    ProjectResourceListResponse
)

VALID_RESOURCE_TYPES = {"document", "workflow", "agent"}

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def _assert_can_manage_project(self, workspace_id: uuid.UUID, project_id: uuid.UUID, actor_id: uuid.UUID):
        actor_user = self.db.query(User).filter(User.id == actor_id).first()
        if actor_user and actor_user.role and actor_user.role.name == "admin":
            return

        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == actor_id
        ).first()
        if ws_member and ws_member.role in ["owner", "admin"]:
            return

        proj_member = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == actor_id,
            ProjectMembership.status == "active"
        ).first()
        if proj_member and proj_member.role in ["owner", "editor"]:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage project."
        )

    def create_project(
        self,
        workspace_id: uuid.UUID,
        name: str,
        description: Optional[str],
        creator_id: uuid.UUID
    ) -> ProjectResponse:
        clean_name = name.strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Project name cannot be empty.")

        existing = self.db.query(Project).filter(
            Project.workspace_id == workspace_id,
            Project.name == clean_name
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Project '{clean_name}' already exists in workspace.")

        project = Project(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=clean_name,
            description=description,
            status="active",
            created_by=creator_id
        )
        self.db.add(project)
        self.db.flush()

        # Add creator as owner
        membership = ProjectMembership(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=creator_id,
            role="owner",
            status="active"
        )
        self.db.add(membership)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=creator_id,
            action="PROJECT_CREATED",
            details=f"Project '{clean_name}' ({project.id}) created."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        self.db.refresh(project)

        # Platform Event
        try:
            creator_u = self.db.query(User).filter(User.id == creator_id).first()
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=creator_id,
                payload={"action": "PROJECT_CREATED", "project_id": str(project.id), "name": clean_name}
            ))
        except Exception:
            pass

        return self.get_project(workspace_id=workspace_id, project_id=project.id, actor_id=creator_id)

    def get_project(self, workspace_id: uuid.UUID, project_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None) -> ProjectResponse:
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id
        ).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        owner_membership = self.db.query(ProjectMembership, User).join(
            User, ProjectMembership.user_id == User.id
        ).filter(
            ProjectMembership.project_id == project.id,
            ProjectMembership.role == "owner",
            ProjectMembership.status == "active"
        ).first()

        member_count = self.db.query(func.count(ProjectMembership.id)).filter(
            ProjectMembership.project_id == project.id,
            ProjectMembership.status == "active"
        ).scalar() or 0

        resource_count = self.db.query(func.count(ProjectResource.id)).filter(
            ProjectResource.project_id == project.id
        ).scalar() or 0

        owner_id = owner_membership[0].user_id if owner_membership else project.created_by
        owner_name = owner_membership[1].username if owner_membership else "creator"

        return ProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            status=project.status,
            created_by=project.created_by,
            created_at=project.created_at,
            updated_at=project.updated_at,
            owner_id=owner_id,
            owner_name=owner_name,
            member_count=member_count,
            resource_count=resource_count
        )

    def list_projects(
        self,
        workspace_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[str] = "active",
        search: Optional[str] = None
    ) -> ProjectListResponse:
        query = self.db.query(Project).filter(Project.workspace_id == workspace_id)

        if status_filter:
            query = query.filter(Project.status == status_filter)

        if search:
            query = query.filter(Project.name.ilike(f"%{search.strip()}%"))

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        projects = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size).all()

        items = [
            self.get_project(workspace_id=workspace_id, project_id=p.id, actor_id=actor_id)
            for p in projects
        ]

        return ProjectListResponse(
            total=total,
            page=page,
            page_size=page_size,
            projects=items
        )

    def update_project(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        name: Optional[str],
        description: Optional[str],
        actor_id: uuid.UUID
    ) -> ProjectResponse:
        self._assert_can_manage_project(workspace_id, project_id, actor_id)

        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id
        ).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        if project.status == "archived":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit archived project.")

        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Project name cannot be empty.")
            if clean_name != project.name:
                collision = self.db.query(Project).filter(
                    Project.workspace_id == workspace_id,
                    Project.name == clean_name,
                    Project.id != project_id
                ).first()
                if collision:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Project '{clean_name}' already exists.")
                project.name = clean_name

        if description is not None:
            project.description = description

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_UPDATED",
            details=f"Project '{project.name}' ({project.id}) updated."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        return self.get_project(workspace_id=workspace_id, project_id=project.id, actor_id=actor_id)

    def archive_project(self, workspace_id: uuid.UUID, project_id: uuid.UUID, actor_id: uuid.UUID) -> ProjectResponse:
        self._assert_can_manage_project(workspace_id, project_id, actor_id)
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id
        ).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        project.status = "archived"
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_ARCHIVED",
            details=f"Project '{project.name}' ({project.id}) archived."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        return self.get_project(workspace_id=workspace_id, project_id=project.id, actor_id=actor_id)

    def restore_project(self, workspace_id: uuid.UUID, project_id: uuid.UUID, actor_id: uuid.UUID) -> ProjectResponse:
        self._assert_can_manage_project(workspace_id, project_id, actor_id)
        project = self.db.query(Project).filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id
        ).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        project.status = "active"
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_RESTORED",
            details=f"Project '{project.name}' ({project.id}) restored."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        return self.get_project(workspace_id=workspace_id, project_id=project.id, actor_id=actor_id)

    def transfer_ownership(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        actor_id: uuid.UUID
    ) -> ProjectResponse:
        self._assert_can_manage_project(workspace_id, project_id, actor_id)

        target_member = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == target_user_id,
            ProjectMembership.status == "active"
        ).first()
        if not target_member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user is not an active member of this project.")

        existing_owners = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.role == "owner",
            ProjectMembership.status == "active"
        ).all()
        for om in existing_owners:
            om.role = "editor"

        target_member.role = "owner"

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_OWNER_TRANSFERRED",
            details=f"Project '{project_id}' ownership transferred to user '{target_user_id}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        return self.get_project(workspace_id=workspace_id, project_id=project_id, actor_id=actor_id)

    # MEMBERSHIP
    def list_members(self, workspace_id: uuid.UUID, project_id: uuid.UUID, page: int = 1, page_size: int = 50) -> ProjectMemberListResponse:
        project = self.db.query(Project).filter(Project.id == project_id, Project.workspace_id == workspace_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        query = self.db.query(ProjectMembership, User).join(
            User, ProjectMembership.user_id == User.id
        ).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.status == "active",
            User.is_active == True,
            User.is_deleted == False
        )

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        results = query.order_by(ProjectMembership.created_at.asc()).offset(offset).limit(page_size).all()

        items = [
            ProjectMemberResponse(
                id=pm.id,
                project_id=pm.project_id,
                user_id=pm.user_id,
                username=u.username,
                email=u.email,
                role=pm.role,
                status=pm.status,
                created_at=pm.created_at,
                updated_at=pm.updated_at
            )
            for pm, u in results
        ]

        return ProjectMemberListResponse(total=total, page=page, page_size=page_size, members=items)

    def add_member(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "viewer",
        actor_id: Optional[uuid.UUID] = None
    ) -> ProjectMemberResponse:
        if actor_id:
            self._assert_can_manage_project(workspace_id, project_id, actor_id)

        if role not in ["owner", "editor", "viewer"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid project role: '{role}'.")

        ws_member = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        if not ws_member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a member of the workspace.")

        existing = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id
        ).first()

        user = self.db.query(User).filter(User.id == user_id).first()

        if existing:
            if existing.status == "active":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already an active project member.")
            existing.status = "active"
            existing.role = role
            membership = existing
        else:
            membership = ProjectMembership(
                id=uuid.uuid4(),
                project_id=project_id,
                user_id=user_id,
                role=role,
                status="active"
            )
            self.db.add(membership)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_MEMBER_ADDED",
            details=f"User '{user_id}' added to project '{project_id}' with role '{role}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        self.db.refresh(membership)

        return ProjectMemberResponse(
            id=membership.id,
            project_id=membership.project_id,
            user_id=membership.user_id,
            username=user.username if user else "user",
            email=user.email if user else "user@internal",
            role=membership.role,
            status=membership.status,
            created_at=membership.created_at,
            updated_at=membership.updated_at
        )

    def update_member_role(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        actor_id: uuid.UUID
    ) -> ProjectMemberResponse:
        self._assert_can_manage_project(workspace_id, project_id, actor_id)

        if role not in ["owner", "editor", "viewer"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid project role: '{role}'.")

        member = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
            ProjectMembership.status == "active"
        ).first()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")

        if member.role == "owner" and role != "owner":
            owner_count = self.db.query(func.count(ProjectMembership.id)).filter(
                ProjectMembership.project_id == project_id,
                ProjectMembership.role == "owner",
                ProjectMembership.status == "active"
            ).scalar() or 0
            if owner_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the sole project owner. Transfer ownership instead.")

        member.role = role
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_MEMBER_ROLE_CHANGED",
            details=f"User '{user_id}' project role changed to '{role}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        self.db.refresh(member)

        user = self.db.query(User).filter(User.id == user_id).first()
        return ProjectMemberResponse(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            username=user.username if user else "user",
            email=user.email if user else "user@internal",
            role=member.role,
            status=member.status,
            created_at=member.created_at,
            updated_at=member.updated_at
        )

    def remove_member(self, workspace_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID, actor_id: uuid.UUID):
        self._assert_can_manage_project(workspace_id, project_id, actor_id)

        member = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
            ProjectMembership.status == "active"
        ).first()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")

        if member.role == "owner":
            owner_count = self.db.query(func.count(ProjectMembership.id)).filter(
                ProjectMembership.project_id == project_id,
                ProjectMembership.role == "owner",
                ProjectMembership.status == "active"
            ).scalar() or 0
            if owner_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the sole project owner. Transfer ownership before removal.")

        member.status = "removed"
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_MEMBER_REMOVED",
            details=f"User '{user_id}' removed from project '{project_id}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass

    # RESOURCES
    def list_resources(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        resource_type: Optional[str] = None
    ) -> ProjectResourceListResponse:
        project = self.db.query(Project).filter(Project.id == project_id, Project.workspace_id == workspace_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        query = self.db.query(ProjectResource).filter(
            ProjectResource.project_id == project_id,
            ProjectResource.workspace_id == workspace_id
        )
        if resource_type:
            query = query.filter(ProjectResource.resource_type == resource_type)

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        resources = query.order_by(ProjectResource.created_at.desc()).offset(offset).limit(page_size).all()

        items = []
        for r in resources:
            r_name = f"{r.resource_type}:{r.resource_id}"
            if r.resource_type == "document":
                try:
                    doc = self.db.query(Document).filter(Document.id == uuid.UUID(r.resource_id)).first()
                    if doc:
                        r_name = doc.filename
                except Exception:
                    pass
            elif r.resource_type == "workflow":
                try:
                    wf = self.db.query(Workflow).filter(Workflow.id == uuid.UUID(r.resource_id)).first()
                    if wf:
                        r_name = wf.name
                except Exception:
                    pass

            items.append(ProjectResourceResponse(
                id=r.id,
                project_id=r.project_id,
                workspace_id=r.workspace_id,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                resource_name=r_name,
                created_by=r.created_by,
                created_at=r.created_at
            ))

        return ProjectResourceListResponse(total=total, page=page, page_size=page_size, resources=items)

    def link_resource(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        actor_id: uuid.UUID
    ) -> ProjectResourceResponse:
        self._assert_can_manage_project(workspace_id, project_id, actor_id)

        clean_type = resource_type.strip().lower()
        if clean_type not in VALID_RESOURCE_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid resource type '{resource_type}'.")

        project = self.db.query(Project).filter(Project.id == project_id, Project.workspace_id == workspace_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

        # Verify resource belongs to same workspace
        r_name = None
        if clean_type == "document":
            try:
                doc = self.db.query(Document).filter(
                    Document.id == uuid.UUID(resource_id),
                    Document.workspace_id == workspace_id
                ).first()
                if not doc:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in current workspace.")
                r_name = doc.filename
            except ValueError:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid document ID format.")
        elif clean_type == "workflow":
            try:
                wf = self.db.query(Workflow).filter(
                    Workflow.id == uuid.UUID(resource_id),
                    Workflow.workspace_id == workspace_id
                ).first()
                if not wf:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found in current workspace.")
                r_name = wf.name
            except ValueError:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid workflow ID format.")

        existing = self.db.query(ProjectResource).filter(
            ProjectResource.project_id == project_id,
            ProjectResource.resource_type == clean_type,
            ProjectResource.resource_id == resource_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource is already linked to this project.")

        link = ProjectResource(
            id=uuid.uuid4(),
            project_id=project_id,
            workspace_id=workspace_id,
            resource_type=clean_type,
            resource_id=resource_id,
            created_by=actor_id
        )
        self.db.add(link)

        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_RESOURCE_LINKED",
            details=f"Resource '{clean_type}:{resource_id}' linked to project '{project_id}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
        self.db.refresh(link)

        return ProjectResourceResponse(
            id=link.id,
            project_id=link.project_id,
            workspace_id=link.workspace_id,
            resource_type=link.resource_type,
            resource_id=link.resource_id,
            resource_name=r_name or f"{clean_type}:{resource_id}",
            created_by=link.created_by,
            created_at=link.created_at
        )

    def unlink_resource(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        actor_id: uuid.UUID
    ):
        self._assert_can_manage_project(workspace_id, project_id, actor_id)

        clean_type = resource_type.strip().lower()
        link = self.db.query(ProjectResource).filter(
            ProjectResource.project_id == project_id,
            ProjectResource.workspace_id == workspace_id,
            ProjectResource.resource_type == clean_type,
            ProjectResource.resource_id == resource_id
        ).first()
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked project resource not found.")

        self.db.delete(link)
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=actor_id,
            action="PROJECT_RESOURCE_UNLINKED",
            details=f"Resource '{clean_type}:{resource_id}' unlinked from project '{project_id}'."
        )
        self.db.add(audit)
        self.db.commit()
        try:
            RealtimeConnectionManager.get_instance().revoke_user_channel(workspace_id, user_id, f"project:{project_id}")
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={"action": "PROJECT_MEMBER_REMOVED", "project_id": str(project_id), "user_id": str(user_id)}
            ))
        except Exception:
            pass
