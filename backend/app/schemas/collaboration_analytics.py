import uuid
import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PeriodComparison(BaseModel):
    current: int
    previous: int
    delta: int
    growth_rate: float

class CollaborationOverviewResponse(BaseModel):
    workspace_id: uuid.UUID
    time_window: str
    active_users: int
    total_members: int
    active_teams: int
    active_projects: int
    total_comments: int
    root_comments: int
    total_replies: int
    total_mentions: int
    notifications_generated: int
    notifications_read: int
    total_activities: int
    engagement_rate: float
    health_status: str # HEALTHY, MODERATE, LOW
    activity_growth: PeriodComparison
    comment_growth: PeriodComparison

class TeamAnalyticsItem(BaseModel):
    team_id: uuid.UUID
    team_name: str
    member_count: int
    active_members: int
    comment_count: int
    activity_count: int
    engagement_rate: float
    health_status: str

class TeamAnalyticsListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    teams: List[TeamAnalyticsItem] = Field(default_factory=list)

class ProjectAnalyticsItem(BaseModel):
    project_id: uuid.UUID
    project_name: str
    member_count: int
    active_members: int
    resource_count: int
    comment_count: int
    reply_count: int
    activity_count: int
    engagement_rate: float

class ProjectAnalyticsListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 50
    projects: List[ProjectAnalyticsItem] = Field(default_factory=list)

class ActivityTimeSeriesPoint(BaseModel):
    date: str
    count: int
    by_type: Dict[str, int] = Field(default_factory=dict)

class ActivityAnalyticsResponse(BaseModel):
    time_window: str
    total_activities: int
    series: List[ActivityTimeSeriesPoint] = Field(default_factory=list)

class CommentAnalyticsResponse(BaseModel):
    total_comments: int
    root_comments: int
    replies: int
    reply_to_root_ratio: float
    avg_comments_per_project: float

class TopMentionedUser(BaseModel):
    user_id: uuid.UUID
    username: str
    mention_count: int

class MentionAnalyticsResponse(BaseModel):
    total_mentions: int
    unique_mentioned_users: int
    top_mentioned: List[TopMentionedUser] = Field(default_factory=list)

class NotificationAnalyticsResponse(BaseModel):
    total_generated: int
    total_read: int
    total_unread: int
    read_rate: float
    by_type: Dict[str, int] = Field(default_factory=dict)

class ResourceCollaborationResponse(BaseModel):
    total_linked_resources: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    commented_resources: int

class TopContributorItem(BaseModel):
    user_id: uuid.UUID
    username: str
    activity_count: int
    comment_count: int
    mention_count: int

class TopContributorsResponse(BaseModel):
    contributors: List[TopContributorItem] = Field(default_factory=list)
