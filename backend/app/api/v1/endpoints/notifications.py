from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
from typing import Optional

from app.database.session import get_db
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate
)
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.notification import NotificationService

router = APIRouter(tags=["Notifications & Real-Time Delivery"])

@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    return service.list_notifications(
        workspace_id=workspace_member.workspace_id,
        user_id=current_user.id,
        status=status,
        type=type,
        page=page,
        page_size=page_size
    )

@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    count = service.get_unread_count(
        workspace_id=workspace_member.workspace_id,
        user_id=current_user.id
    )
    return UnreadCountResponse(unread_count=count)

@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    return service.mark_as_read(
        workspace_id=workspace_member.workspace_id,
        user_id=current_user.id,
        notification_id=notification_id
    )

@router.post("/notifications/read-all", response_model=UnreadCountResponse)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    service.mark_all_as_read(
        workspace_id=workspace_member.workspace_id,
        user_id=current_user.id
    )
    return UnreadCountResponse(unread_count=0)

@router.get("/notifications/preferences", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    return service.get_preferences(user_id=current_user.id)

@router.put("/notifications/preferences", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    service.update_preference(
        user_id=current_user.id,
        notification_type=payload.notification_type,
        in_app_enabled=payload.in_app_enabled,
        email_enabled=payload.email_enabled,
        push_enabled=payload.push_enabled
    )
    return service.get_preferences(user_id=current_user.id)
