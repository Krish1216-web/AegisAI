import uuid
import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from loguru import logger

from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType
from app.core.collaboration.realtime import RealtimeConnectionManager
from app.core.email.provider import get_email_provider
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationPreferenceItem,
    NotificationPreferenceResponse
)

SUPPORTED_TYPES = [
    "MENTION",
    "COMMENT_REPLY",
    "COMMENT_ON_PROJECT",
    "PROJECT_MEMBER_ADDED",
    "PROJECT_MEMBER_REMOVED",
    "PROJECT_ROLE_CHANGED",
    "TEAM_MEMBER_ADDED",
    "TEAM_MEMBER_REMOVED",
    "TEAM_INVITATION",
    "TEAM_ROLE_CHANGED"
]

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        workspace_id: uuid.UUID,
        recipient_user_id: uuid.UUID,
        type: str,
        title: str,
        body: str,
        actor_user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        team_id: Optional[uuid.UUID] = None,
        comment_id: Optional[uuid.UUID] = None,
        mention_id: Optional[uuid.UUID] = None,
    ) -> Optional[Notification]:
        # 1. Prevent self-notification
        if actor_user_id and actor_user_id == recipient_user_id:
            return None

        # 2. Check user notification preferences
        pref = self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == recipient_user_id,
            NotificationPreference.notification_type.in_(["all", type])
        ).first()

        in_app_enabled = pref.in_app_enabled if pref else True
        email_enabled = pref.email_enabled if pref else True

        if not in_app_enabled and not email_enabled:
            return None

        # 3. Deduplication (recent duplicate check within 60 seconds)
        window = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)
        existing = self.db.query(Notification).filter(
            Notification.recipient_user_id == recipient_user_id,
            Notification.type == type,
            Notification.project_id == project_id,
            Notification.team_id == team_id,
            Notification.comment_id == comment_id,
            Notification.created_at >= window
        ).first()
        if existing:
            return existing

        # 4. Create Notification record
        notif = Notification(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            type=type,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            team_id=team_id,
            comment_id=comment_id,
            mention_id=mention_id,
            status="unread"
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)

        # 5. Real-Time WebSocket Delivery
        try:
            unread_count = self.get_unread_count(workspace_id, recipient_user_id)
            actor = self.db.query(User).filter(User.id == actor_user_id).first() if actor_user_id else None
            evt_payload = {
                "action": "NOTIFICATION_CREATED",
                "notification_id": str(notif.id),
                "type": notif.type,
                "title": notif.title,
                "body": notif.body,
                "project_id": str(project_id) if project_id else None,
                "unread_count": unread_count,
                "actor_name": actor.username if actor else "System"
            }
            # Broadcast to workspace channel (filtered for user on client side or user socket)
            PlatformEventDispatcher.get_instance().dispatch(PlatformEvent(
                event_type=PlatformEventType.COLLABORATION_EVENT,
                workspace_id=workspace_id,
                user_id=recipient_user_id,
                payload=evt_payload
            ))
        except Exception as e:
            logger.warning(f"Failed to dispatch realtime notification event: {e}")

        # 6. Email Dispatch
        if email_enabled:
            recipient = self.db.query(User).filter(User.id == recipient_user_id).first()
            if recipient and recipient.email:
                provider = get_email_provider()
                provider.send_email(
                    to_email=recipient.email,
                    subject=f"[AegisAI] {title}",
                    body_text=f"Hi {recipient.username},\n\n{body}\n\nBest,\nAegisAI Team"
                )

        return notif

    def list_notifications(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> NotificationListResponse:
        query = self.db.query(Notification).filter(
            Notification.workspace_id == workspace_id,
            Notification.recipient_user_id == user_id
        )
        if status:
            query = query.filter(Notification.status == status)
        if type:
            query = query.filter(Notification.type == type)

        total = query.count()
        unread_count = self.get_unread_count(workspace_id, user_id)
        offset = max(0, (page - 1) * page_size)
        records = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size).all()

        items = []
        for n in records:
            actor = self.db.query(User).filter(User.id == n.actor_user_id).first() if n.actor_user_id else None
            items.append(NotificationResponse(
                id=n.id,
                workspace_id=n.workspace_id,
                recipient_user_id=n.recipient_user_id,
                actor_user_id=n.actor_user_id,
                actor_name=actor.username if actor else "System",
                type=n.type,
                title=n.title,
                body=n.body,
                resource_type=n.resource_type,
                resource_id=n.resource_id,
                project_id=n.project_id,
                team_id=n.team_id,
                comment_id=n.comment_id,
                status=n.status,
                read_at=n.read_at,
                created_at=n.created_at
            ))

        return NotificationListResponse(
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
            notifications=items
        )

    def get_unread_count(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return self.db.query(func.count(Notification.id)).filter(
            Notification.workspace_id == workspace_id,
            Notification.recipient_user_id == user_id,
            Notification.status == "unread"
        ).scalar() or 0

    def mark_as_read(self, workspace_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID) -> NotificationResponse:
        notif = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.workspace_id == workspace_id,
            Notification.recipient_user_id == user_id
        ).first()
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

        notif.status = "read"
        notif.read_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()

        actor = self.db.query(User).filter(User.id == notif.actor_user_id).first() if notif.actor_user_id else None
        return NotificationResponse(
            id=notif.id,
            workspace_id=notif.workspace_id,
            recipient_user_id=notif.recipient_user_id,
            actor_user_id=notif.actor_user_id,
            actor_name=actor.username if actor else "System",
            type=notif.type,
            title=notif.title,
            body=notif.body,
            resource_type=notif.resource_type,
            resource_id=notif.resource_id,
            project_id=notif.project_id,
            team_id=notif.team_id,
            comment_id=notif.comment_id,
            status=notif.status,
            read_at=notif.read_at,
            created_at=notif.created_at
        )

    def mark_all_as_read(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        updated = self.db.query(Notification).filter(
            Notification.workspace_id == workspace_id,
            Notification.recipient_user_id == user_id,
            Notification.status == "unread"
        ).update({"status": "read", "read_at": now}, synchronize_session=False)
        self.db.commit()
        return updated

    def get_preferences(self, user_id: uuid.UUID) -> NotificationPreferenceResponse:
        prefs = self.db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).all()
        pref_dict = {p.notification_type: p for p in prefs}

        items = []
        for t in ["all"] + SUPPORTED_TYPES:
            p = pref_dict.get(t)
            items.append(NotificationPreferenceItem(
                notification_type=t,
                in_app_enabled=p.in_app_enabled if p else True,
                email_enabled=p.email_enabled if p else True,
                push_enabled=p.push_enabled if p else True
            ))
        return NotificationPreferenceResponse(user_id=user_id, preferences=items)

    def update_preference(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        in_app_enabled: Optional[bool] = None,
        email_enabled: Optional[bool] = None,
        push_enabled: Optional[bool] = None
    ):
        pref = self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type
        ).first()

        if not pref:
            pref = NotificationPreference(
                id=uuid.uuid4(),
                user_id=user_id,
                notification_type=notification_type,
                in_app_enabled=in_app_enabled if in_app_enabled is not None else True,
                email_enabled=email_enabled if email_enabled is not None else True,
                push_enabled=push_enabled if push_enabled is not None else True
            )
            self.db.add(pref)
        else:
            if in_app_enabled is not None:
                pref.in_app_enabled = in_app_enabled
            if email_enabled is not None:
                pref.email_enabled = email_enabled
            if push_enabled is not None:
                pref.push_enabled = push_enabled

        self.db.commit()
