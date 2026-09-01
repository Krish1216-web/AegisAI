from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
import datetime
from typing import Optional

from app.database.session import get_db
from app.schemas.collaboration_analytics import (
    CollaborationOverviewResponse,
    TeamAnalyticsListResponse,
    ProjectAnalyticsListResponse,
    ActivityAnalyticsResponse,
    CommentAnalyticsResponse,
    MentionAnalyticsResponse,
    NotificationAnalyticsResponse,
    ResourceCollaborationResponse,
    TopContributorsResponse
)
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.collaboration_analytics import CollaborationAnalyticsService

router = APIRouter(prefix="/collaboration/analytics", tags=["Collaboration Analytics"])

@router.get("/overview", response_model=CollaborationOverviewResponse)
def get_overview(
    time_window: str = Query("7d"),
    start_date: Optional[datetime.datetime] = Query(None),
    end_date: Optional[datetime.datetime] = Query(None),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_overview(
        workspace_id=workspace_member.workspace_id,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/teams", response_model=TeamAnalyticsListResponse)
def get_teams(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_team_analytics(
        workspace_id=workspace_member.workspace_id,
        page=page,
        page_size=page_size,
        search=search
    )

@router.get("/projects", response_model=ProjectAnalyticsListResponse)
def get_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_project_analytics(
        workspace_id=workspace_member.workspace_id,
        page=page,
        page_size=page_size,
        search=search
    )

@router.get("/activity", response_model=ActivityAnalyticsResponse)
def get_activity(
    time_window: str = Query("7d"),
    start_date: Optional[datetime.datetime] = Query(None),
    end_date: Optional[datetime.datetime] = Query(None),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_activity_time_series(
        workspace_id=workspace_member.workspace_id,
        time_window=time_window,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/comments", response_model=CommentAnalyticsResponse)
def get_comments(
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_comment_analytics(workspace_id=workspace_member.workspace_id)

@router.get("/mentions", response_model=MentionAnalyticsResponse)
def get_mentions(
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_mention_analytics(workspace_id=workspace_member.workspace_id)

@router.get("/notifications", response_model=NotificationAnalyticsResponse)
def get_notifications(
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_notification_analytics(workspace_id=workspace_member.workspace_id)

@router.get("/resources", response_model=ResourceCollaborationResponse)
def get_resources(
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_resource_analytics(workspace_id=workspace_member.workspace_id)

@router.get("/top-contributors", response_model=TopContributorsResponse)
def get_top_contributors(
    limit: int = Query(10, ge=1, le=50),
    workspace_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    service = CollaborationAnalyticsService(db)
    return service.get_top_contributors(workspace_id=workspace_member.workspace_id, limit=limit)
