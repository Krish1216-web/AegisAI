import uuid
import re
import datetime
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from loguru import logger

from app.models.comment import Comment, CommentMention
from app.models.workspace import WorkspaceMember
from app.models.user import User
from app.models.project import Project, ProjectMembership, ProjectResource
from app.models.document import Document
from app.models.workflow import Workflow
from app.models.audit import AuditLog, ActivityLog
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType
from app.core.collaboration.realtime import RealtimeConnectionManager
from app.schemas.comment import (
    CommentResponse,
    CommentListResponse,
    CommentMentionResponse,
    MentionableUserResponse,
    ActivityItemResponse,
    ActivityListResponse
)

VALID_RESOURCE_TYPES = {"document", "workflow", "agent"}
MAX_COMMENT_DEPTH = 10

class CommentService:
    def __init__(self, db: Session):
        self.db = db

    def extract_mentions(self, text: str) -> Set[str]:
        # Regex to find @username
        pattern = r'(?<!\w)@([a-zA-Z0-9_.-]{1,50})'
        matches = re.findall(pattern, text)
        return {m.lower() for m in matches}

    def _validate_context(
        self,
        workspace_id: uuid.UUID,
        project_id: Optional[uuid.UUID],
        resource_type: Optional[str],
        resource_id: Optional[str],
        parent_comment_id: Optional[uuid.UUID]
    ):
        if resource_type:
            clean_type = resource_type.strip().lower()
            if clean_type not in VALID_RESOURCE_TYPES:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid resource type '{resource_type}'.")
            if not resource_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Resource ID required when resource_type is specified.")

            # Validate resource in workspace
            if clean_type == "document":
                try:
                    doc = self.db.query(Document).filter(
                        Document.id == uuid.UUID(resource_id),
                        Document.workspace_id == workspace_id
                    ).first()
                    if not doc:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in workspace.")
                except ValueError:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid document UUID format.")
            elif clean_type == "workflow":
                try:
                    wf = self.db.query(Workflow).filter(
                        Workflow.id == uuid.UUID(resource_id),
                        Workflow.workspace_id == workspace_id
                    ).first()
                    if not wf:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found in workspace.")
                except ValueError:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid workflow UUID format.")

        if project_id:
            project = self.db.query(Project).filter(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
                Project.status == "active"
            ).first()
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in workspace.")

        if parent_comment_id:
            parent = self.db.query(Comment).filter(
                Comment.id == parent_comment_id,
                Comment.workspace_id == workspace_id
            ).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found in workspace.")
            if parent.project_id != project_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent comment belongs to a different project context.")
            if parent.resource_type != resource_type or parent.resource_id != resource_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent comment belongs to a different resource context.")

            # Calculate hierarchy depth
            depth = 1
            curr = parent
            while curr.parent_comment_id and depth <= MAX_COMMENT_DEPTH + 1:
                depth += 1
                curr = self.db.query(Comment).filter(Comment.id == curr.parent_comment_id).first()
                if not curr:
                    break
            if depth > MAX_COMMENT_DEPTH:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum thread depth ({MAX_COMMENT_DEPTH}) exceeded.")

    def create_comment(
        self,
        workspace_id: uuid.UUID,
        author_id: uuid.UUID,
        body: str,
        project_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        parent_comment_id: Optional[uuid.UUID] = None
    ) -> CommentResponse:
        clean_body = body.strip()
        if not clean_body:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment body cannot be empty.")

        self._validate_context(workspace_id, project_id, resource_type, resource_id, parent_comment_id)

        comment = Comment(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            author_id=author_id,
            project_id=project_id,
            resource_type=resource_type.strip().lower() if resource_type else None,
            resource_id=resource_id,
            parent_comment_id=parent_comment_id,
            body=clean_body,
            status="active"
        )
        self.db.add(comment)
        self.db.flush()

        # Parse & persist mentions
        mentioned_usernames = self.extract_mentions(clean_body)
        mention_responses = []
        if mentioned_usernames:
            # Query eligible workspace users
            eligible_users = self.db.query(User).join(
                WorkspaceMember, WorkspaceMember.user_id == User.id
            ).filter(
                WorkspaceMember.workspace_id == workspace_id,
                User.is_active == True,
                User.is_deleted == False
            ).all()

            username_to_user = {u.username.lower(): u for u in eligible_users}

            for uname in mentioned_usernames:
                if uname in username_to_user:
                    m_user = username_to_user[uname]
                    mention = CommentMention(
                        id=uuid.uuid4(),
                        comment_id=comment.id,
                        mentioned_user_id=m_user.id
                    )
                    self.db.add(mention)
                    mention_responses.append(CommentMentionResponse(user_id=m_user.id, username=m_user.username))

        # Activity Log
        author = self.db.query(User).filter(User.id == author_id).first()
        author_name = author.username if author else "User"
        activity_desc = f"{author_name} commented on {('project ' + str(project_id)) if project_id else 'workspace'}"
        activity = ActivityLog(
            id=uuid.uuid4(),
            user_id=author_id,
            activity_type="COMMENT_CREATED",
            description=activity_desc
        )
        self.db.add(activity)

        # Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=author_id,
            action="COMMENT_CREATED",
            details=f"Comment ({comment.id}) created by user {author_id}."
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(comment)

        # Real-time Broadcast
        try:
            evt_payload = {
                "action": "COMMENT_CREATED",
                "comment_id": str(comment.id),
                "project_id": str(project_id) if project_id else None,
                "resource_type": comment.resource_type,
                "resource_id": comment.resource_id,
                "author_id": str(author_id),
                "author_name": author_name
            }
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=author_id,
                payload=evt_payload
            ))
        except Exception:
            pass

        return CommentResponse(
            id=comment.id,
            workspace_id=comment.workspace_id,
            author_id=comment.author_id,
            author_name=author_name,
            project_id=comment.project_id,
            resource_type=comment.resource_type,
            resource_id=comment.resource_id,
            parent_comment_id=comment.parent_comment_id,
            body=comment.body,
            status=comment.status,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            edited_at=comment.edited_at,
            deleted_at=comment.deleted_at,
            reply_count=0,
            mentions=mention_responses
        )

    def list_comments(
        self,
        workspace_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        parent_comment_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 50
    ) -> CommentListResponse:
        query = self.db.query(Comment).filter(Comment.workspace_id == workspace_id)

        if project_id:
            query = query.filter(Comment.project_id == project_id)
        if resource_type:
            query = query.filter(Comment.resource_type == resource_type.strip().lower())
        if resource_id:
            query = query.filter(Comment.resource_id == resource_id)
        if parent_comment_id is not None:
            query = query.filter(Comment.parent_comment_id == parent_comment_id)

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        comments = query.order_by(Comment.created_at.asc()).offset(offset).limit(page_size).all()

        items = []
        for c in comments:
            author = self.db.query(User).filter(User.id == c.author_id).first() if c.author_id else None
            author_name = author.username if author else "Former Member"

            reply_count = self.db.query(func.count(Comment.id)).filter(
                Comment.parent_comment_id == c.id,
                Comment.status == "active"
            ).scalar() or 0

            mentions_query = self.db.query(CommentMention, User).join(
                User, CommentMention.mentioned_user_id == User.id
            ).filter(CommentMention.comment_id == c.id).all()

            mentions_list = [
                CommentMentionResponse(user_id=u.id, username=u.username)
                for cm, u in mentions_query
            ]

            display_body = c.body if c.status == "active" else "This comment was deleted."

            items.append(CommentResponse(
                id=c.id,
                workspace_id=c.workspace_id,
                author_id=c.author_id,
                author_name=author_name,
                project_id=c.project_id,
                resource_type=c.resource_type,
                resource_id=c.resource_id,
                parent_comment_id=c.parent_comment_id,
                body=display_body,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
                edited_at=c.edited_at,
                deleted_at=c.deleted_at,
                reply_count=reply_count,
                mentions=mentions_list
            ))

        return CommentListResponse(total=total, page=page, page_size=page_size, comments=items)

    def update_comment(
        self,
        workspace_id: uuid.UUID,
        comment_id: uuid.UUID,
        body: str,
        actor_id: uuid.UUID
    ) -> CommentResponse:
        clean_body = body.strip()
        if not clean_body:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment body cannot be empty.")

        comment = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.workspace_id == workspace_id
        ).first()
        if not comment or comment.status == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        # Verify permission: author or workspace owner/admin
        if comment.author_id != actor_id:
            actor = self.db.query(User).filter(User.id == actor_id).first()
            is_admin = actor and actor.role and actor.role.name in ["admin", "super admin"]
            ws_member = self.db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == actor_id
            ).first()
            if not is_admin and (not ws_member or ws_member.role not in ["owner", "admin"]):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit another user's comment.")

        comment.body = clean_body
        comment.edited_at = datetime.datetime.now(datetime.timezone.utc)

        # Update mentions
        self.db.query(CommentMention).filter(CommentMention.comment_id == comment.id).delete()
        mentioned_usernames = self.extract_mentions(clean_body)
        mention_responses = []
        if mentioned_usernames:
            eligible_users = self.db.query(User).join(
                WorkspaceMember, WorkspaceMember.user_id == User.id
            ).filter(
                WorkspaceMember.workspace_id == workspace_id,
                User.is_active == True,
                User.is_deleted == False
            ).all()
            username_to_user = {u.username.lower(): u for u in eligible_users}
            for uname in mentioned_usernames:
                if uname in username_to_user:
                    m_user = username_to_user[uname]
                    mention = CommentMention(
                        id=uuid.uuid4(),
                        comment_id=comment.id,
                        mentioned_user_id=m_user.id
                    )
                    self.db.add(mention)
                    mention_responses.append(CommentMentionResponse(user_id=m_user.id, username=m_user.username))

        self.db.commit()

        # Real-time Broadcast
        try:
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={
                    "action": "COMMENT_UPDATED",
                    "comment_id": str(comment.id),
                    "project_id": str(comment.project_id) if comment.project_id else None
                }
            ))
        except Exception:
            pass

        author = self.db.query(User).filter(User.id == comment.author_id).first()
        return CommentResponse(
            id=comment.id,
            workspace_id=comment.workspace_id,
            author_id=comment.author_id,
            author_name=author.username if author else "User",
            project_id=comment.project_id,
            resource_type=comment.resource_type,
            resource_id=comment.resource_id,
            parent_comment_id=comment.parent_comment_id,
            body=comment.body,
            status=comment.status,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            edited_at=comment.edited_at,
            deleted_at=comment.deleted_at,
            reply_count=0,
            mentions=mention_responses
        )

    def delete_comment(
        self,
        workspace_id: uuid.UUID,
        comment_id: uuid.UUID,
        actor_id: uuid.UUID
    ):
        comment = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.workspace_id == workspace_id
        ).first()
        if not comment or comment.status == "deleted":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        # Permission check
        if comment.author_id != actor_id:
            actor = self.db.query(User).filter(User.id == actor_id).first()
            is_admin = actor and actor.role and actor.role.name in ["admin", "super admin"]
            ws_member = self.db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == actor_id
            ).first()
            if not is_admin and (not ws_member or ws_member.role not in ["owner", "admin"]):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete another user's comment.")

        comment.status = "deleted"
        comment.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()

        # Real-time Broadcast
        try:
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=actor_id,
                payload={
                    "action": "COMMENT_DELETED",
                    "comment_id": str(comment.id),
                    "project_id": str(comment.project_id) if comment.project_id else None
                }
            ))
        except Exception:
            pass

    def list_mentionable_users(
        self,
        workspace_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        limit: int = 20
    ) -> List[MentionableUserResponse]:
        query = self.db.query(User).join(
            WorkspaceMember, WorkspaceMember.user_id == User.id
        ).filter(
            WorkspaceMember.workspace_id == workspace_id,
            User.is_active == True,
            User.is_deleted == False
        )

        if project_id:
            query = query.join(
                ProjectMembership, ProjectMembership.user_id == User.id
            ).filter(
                ProjectMembership.project_id == project_id,
                ProjectMembership.status == "active"
            )

        if search:
            query = query.filter(User.username.ilike(f"%{search.strip()}%"))

        users = query.order_by(User.username.asc()).limit(limit).all()
        return [
            MentionableUserResponse(user_id=u.id, username=u.username, email=u.email)
            for u in users
        ]

    def list_activity(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50
    ) -> ActivityListResponse:
        query = self.db.query(ActivityLog)
        total = query.count()
        offset = max(0, (page - 1) * page_size)
        records = query.order_by(ActivityLog.created_at.desc()).offset(offset).limit(page_size).all()

        items = []
        for a in records:
            u = self.db.query(User).filter(User.id == a.user_id).first() if a.user_id else None
            items.append(ActivityItemResponse(
                id=a.id,
                activity_type=a.activity_type,
                description=a.description,
                user_id=a.user_id,
                username=u.username if u else "System",
                created_at=a.created_at
            ))

        return ActivityListResponse(total=total, page=page, page_size=page_size, activities=items)
