import uuid
import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, case
from fastapi import HTTPException, status

from app.models.audit import ActivityLog
from app.models.comment import Comment, CommentMention
from app.models.notification import Notification
from app.models.project import Project, ProjectMembership, ProjectResource
from app.models.team import Team, TeamMembership
from app.models.workspace import WorkspaceMember
from app.models.user import User
from app.schemas.collaboration_analytics import (
    CollaborationOverviewResponse,
    PeriodComparison,
    TeamAnalyticsItem,
    TeamAnalyticsListResponse,
    ProjectAnalyticsItem,
    ProjectAnalyticsListResponse,
    ActivityTimeSeriesPoint,
    ActivityAnalyticsResponse,
    CommentAnalyticsResponse,
    MentionAnalyticsResponse,
    TopMentionedUser,
    NotificationAnalyticsResponse,
    ResourceCollaborationResponse,
    TopContributorItem,
    TopContributorsResponse
)

VALID_PRESETS = {"1h": 1/24, "24h": 1, "7d": 7, "30d": 30, "90d": 90}

class CollaborationAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_time_window(
        self,
        time_window: str = "7d",
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> Tuple[datetime.datetime, datetime.datetime, datetime.datetime, datetime.datetime, str]:
        now = datetime.datetime.now(datetime.timezone.utc)
        if start_date and end_date:
            if start_date >= end_date:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date must be before end_date.")
            duration = end_date - start_date
            if duration.days > 90:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Custom date range cannot exceed 90 days.")
            prev_start = start_date - duration
            prev_end = start_date
            return start_date, end_date, prev_start, prev_end, "custom"

        days = VALID_PRESETS.get(time_window.lower(), 7)
        delta = datetime.timedelta(days=days)
        curr_start = now - delta
        curr_end = now
        prev_start = curr_start - delta
        prev_end = curr_start
        return curr_start, curr_end, prev_start, prev_end, time_window

    def get_overview(
        self,
        workspace_id: uuid.UUID,
        time_window: str = "7d",
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> CollaborationOverviewResponse:
        c_start, c_end, p_start, p_end, window_label = self._resolve_time_window(time_window, start_date, end_date)

        # Total workspace members
        total_members = self.db.query(func.count(WorkspaceMember.id)).filter(
            WorkspaceMember.workspace_id == workspace_id
        ).scalar() or 0

        # Active Teams & Projects
        active_teams = self.db.query(func.count(Team.id)).filter(
            Team.workspace_id == workspace_id,
            Team.status == "active"
        ).scalar() or 0

        active_projects = self.db.query(func.count(Project.id)).filter(
            Project.workspace_id == workspace_id,
            Project.status == "active"
        ).scalar() or 0

        # Current period Activity count & Active Users
        curr_act_query = self.db.query(
            func.count(ActivityLog.id),
            func.count(distinct(ActivityLog.user_id))
        ).filter(
            ActivityLog.created_at >= c_start,
            ActivityLog.created_at <= c_end
        ).first()

        curr_act_count = curr_act_query[0] or 0
        active_users = curr_act_query[1] or 0

        # Previous period Activity count
        prev_act_count = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.created_at >= p_start,
            ActivityLog.created_at <= p_end
        ).scalar() or 0

        # Current Comments & Replies
        curr_comm = self.db.query(
            func.count(Comment.id),
            func.count(case((Comment.parent_comment_id == None, 1))),
            func.count(case((Comment.parent_comment_id != None, 1)))
        ).filter(
            Comment.workspace_id == workspace_id,
            Comment.created_at >= c_start,
            Comment.created_at <= c_end
        ).first()
        total_comments = curr_comm[0] or 0
        root_comments = curr_comm[1] or 0
        total_replies = curr_comm[2] or 0

        # Previous Comments
        prev_comm_count = self.db.query(func.count(Comment.id)).filter(
            Comment.workspace_id == workspace_id,
            Comment.created_at >= p_start,
            Comment.created_at <= p_end
        ).scalar() or 0

        # Mentions
        total_mentions = self.db.query(func.count(CommentMention.id)).join(
            Comment, Comment.id == CommentMention.comment_id
        ).filter(
            Comment.workspace_id == workspace_id,
            CommentMention.created_at >= c_start,
            CommentMention.created_at <= c_end
        ).scalar() or 0

        # Notifications
        notif_stats = self.db.query(
            func.count(Notification.id),
            func.count(case((Notification.status == 'read', 1)))
        ).filter(
            Notification.workspace_id == workspace_id,
            Notification.created_at >= c_start,
            Notification.created_at <= c_end
        ).first()
        notifs_generated = notif_stats[0] or 0
        notifs_read = notif_stats[1] or 0

        # Engagement Rate
        engagement_rate = round(active_users / total_members, 4) if total_members > 0 else 0.0
        health_status = "HEALTHY" if engagement_rate >= 0.50 else ("MODERATE" if engagement_rate >= 0.20 else "LOW")

        # Growth calculations
        act_delta = curr_act_count - prev_act_count
        act_growth = round(act_delta / prev_act_count, 4) if prev_act_count > 0 else (1.0 if curr_act_count > 0 else 0.0)

        comm_delta = total_comments - prev_comm_count
        comm_growth = round(comm_delta / prev_comm_count, 4) if prev_comm_count > 0 else (1.0 if total_comments > 0 else 0.0)

        return CollaborationOverviewResponse(
            workspace_id=workspace_id,
            time_window=window_label,
            active_users=active_users,
            total_members=total_members,
            active_teams=active_teams,
            active_projects=active_projects,
            total_comments=total_comments,
            root_comments=root_comments,
            total_replies=total_replies,
            total_mentions=total_mentions,
            notifications_generated=notifs_generated,
            notifications_read=notifs_read,
            total_activities=curr_act_count,
            engagement_rate=engagement_rate,
            health_status=health_status,
            activity_growth=PeriodComparison(
                current=curr_act_count,
                previous=prev_act_count,
                delta=act_delta,
                growth_rate=act_growth
            ),
            comment_growth=PeriodComparison(
                current=total_comments,
                previous=prev_comm_count,
                delta=comm_delta,
                growth_rate=comm_growth
            )
        )

    def get_team_analytics(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> TeamAnalyticsListResponse:
        query = self.db.query(Team).filter(
            Team.workspace_id == workspace_id,
            Team.status == "active"
        )
        if search:
            query = query.filter(Team.name.ilike(f"%{search.strip()}%"))

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        teams = query.order_by(Team.name.asc()).offset(offset).limit(page_size).all()

        items = []
        for t in teams:
            member_count = self.db.query(func.count(TeamMembership.id)).filter(
                TeamMembership.team_id == t.id
            ).scalar() or 0

            active_members = member_count

            engagement = 1.0 if member_count > 0 else 0.0
            health = "HEALTHY" if engagement >= 0.50 else "MODERATE"

            items.append(TeamAnalyticsItem(
                team_id=t.id,
                team_name=t.name,
                member_count=member_count,
                active_members=active_members,
                comment_count=0,
                activity_count=member_count,
                engagement_rate=engagement,
                health_status=health
            ))

        return TeamAnalyticsListResponse(total=total, page=page, page_size=page_size, teams=items)

    def get_project_analytics(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> ProjectAnalyticsListResponse:
        query = self.db.query(Project).filter(
            Project.workspace_id == workspace_id,
            Project.status == "active"
        )
        if search:
            query = query.filter(Project.name.ilike(f"%{search.strip()}%"))

        total = query.count()
        offset = max(0, (page - 1) * page_size)
        projects = query.order_by(Project.name.asc()).offset(offset).limit(page_size).all()

        items = []
        for p in projects:
            member_count = self.db.query(func.count(ProjectMembership.id)).filter(
                ProjectMembership.project_id == p.id,
                ProjectMembership.status == "active"
            ).scalar() or 0

            resource_count = self.db.query(func.count(ProjectResource.id)).filter(
                ProjectResource.project_id == p.id
            ).scalar() or 0

            comm_stats = self.db.query(
                func.count(Comment.id),
                func.count(case((Comment.parent_comment_id != None, 1)))
            ).filter(
                Comment.project_id == p.id,
                Comment.workspace_id == workspace_id
            ).first()

            comm_count = comm_stats[0] or 0
            rep_count = comm_stats[1] or 0

            engagement = round(member_count / max(1, member_count), 4)

            items.append(ProjectAnalyticsItem(
                project_id=p.id,
                project_name=p.name,
                member_count=member_count,
                active_members=member_count,
                resource_count=resource_count,
                comment_count=comm_count,
                reply_count=rep_count,
                activity_count=comm_count + resource_count,
                engagement_rate=engagement
            ))

        return ProjectAnalyticsListResponse(total=total, page=page, page_size=page_size, projects=items)

    def get_activity_time_series(
        self,
        workspace_id: uuid.UUID,
        time_window: str = "7d",
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> ActivityAnalyticsResponse:
        c_start, c_end, _, _, window_label = self._resolve_time_window(time_window, start_date, end_date)

        records = self.db.query(
            ActivityLog.created_at,
            ActivityLog.activity_type
        ).filter(
            ActivityLog.created_at >= c_start,
            ActivityLog.created_at <= c_end
        ).all()

        date_map: Dict[str, Dict[str, int]] = {}
        for r in records:
            d_str = r[0].strftime("%Y-%m-%d")
            if d_str not in date_map:
                date_map[d_str] = {}
            a_type = r[1]
            date_map[d_str][a_type] = date_map[d_str].get(a_type, 0) + 1

        points = []
        for d_str in sorted(date_map.keys()):
            total_day = sum(date_map[d_str].values())
            points.append(ActivityTimeSeriesPoint(
                date=d_str,
                count=total_day,
                by_type=date_map[d_str]
            ))

        return ActivityAnalyticsResponse(
            time_window=window_label,
            total_activities=len(records),
            series=points
        )

    def get_comment_analytics(self, workspace_id: uuid.UUID) -> CommentAnalyticsResponse:
        comm_stats = self.db.query(
            func.count(Comment.id),
            func.count(case((Comment.parent_comment_id == None, 1))),
            func.count(case((Comment.parent_comment_id != None, 1))),
            func.count(distinct(Comment.project_id))
        ).filter(
            Comment.workspace_id == workspace_id
        ).first()

        total = comm_stats[0] or 0
        roots = comm_stats[1] or 0
        replies = comm_stats[2] or 0
        projects_count = comm_stats[3] or 1

        ratio = round(replies / roots, 4) if roots > 0 else 0.0
        avg_per_proj = round(total / max(1, projects_count), 2)

        return CommentAnalyticsResponse(
            total_comments=total,
            root_comments=roots,
            replies=replies,
            reply_to_root_ratio=ratio,
            avg_comments_per_project=avg_per_proj
        )

    def get_mention_analytics(self, workspace_id: uuid.UUID) -> MentionAnalyticsResponse:
        total_mentions = self.db.query(func.count(CommentMention.id)).join(
            Comment, Comment.id == CommentMention.comment_id
        ).filter(
            Comment.workspace_id == workspace_id
        ).scalar() or 0

        unique_users = self.db.query(func.count(distinct(CommentMention.mentioned_user_id))).join(
            Comment, Comment.id == CommentMention.comment_id
        ).filter(
            Comment.workspace_id == workspace_id
        ).scalar() or 0

        top_rows = self.db.query(
            User.id,
            User.username,
            func.count(CommentMention.id).label("m_count")
        ).join(
            CommentMention, CommentMention.mentioned_user_id == User.id
        ).join(
            Comment, Comment.id == CommentMention.comment_id
        ).filter(
            Comment.workspace_id == workspace_id
        ).group_by(User.id, User.username).order_by(func.count(CommentMention.id).desc()).limit(10).all()

        top_list = [
            TopMentionedUser(user_id=r[0], username=r[1], mention_count=r[2])
            for r in top_rows
        ]

        return MentionAnalyticsResponse(
            total_mentions=total_mentions,
            unique_mentioned_users=unique_users,
            top_mentioned=top_list
        )

    def get_notification_analytics(self, workspace_id: uuid.UUID) -> NotificationAnalyticsResponse:
        stats = self.db.query(
            func.count(Notification.id),
            func.count(case((Notification.status == 'read', 1))),
            func.count(case((Notification.status == 'unread', 1)))
        ).filter(
            Notification.workspace_id == workspace_id
        ).first()

        total = stats[0] or 0
        read_c = stats[1] or 0
        unread_c = stats[2] or 0
        read_rate = round(read_c / total, 4) if total > 0 else 0.0

        type_rows = self.db.query(
            Notification.type,
            func.count(Notification.id)
        ).filter(
            Notification.workspace_id == workspace_id
        ).group_by(Notification.type).all()

        type_dict = {r[0]: r[1] for r in type_rows}

        return NotificationAnalyticsResponse(
            total_generated=total,
            total_read=read_c,
            total_unread=unread_c,
            read_rate=read_rate,
            by_type=type_dict
        )

    def get_resource_analytics(self, workspace_id: uuid.UUID) -> ResourceCollaborationResponse:
        res_rows = self.db.query(
            ProjectResource.resource_type,
            func.count(ProjectResource.id)
        ).join(
            Project, Project.id == ProjectResource.project_id
        ).filter(
            Project.workspace_id == workspace_id
        ).group_by(ProjectResource.resource_type).all()

        res_dict = {r[0]: r[1] for r in res_rows}
        total_linked = sum(res_dict.values())

        commented_count = self.db.query(func.count(distinct(Comment.resource_id))).filter(
            Comment.workspace_id == workspace_id,
            Comment.resource_type != None
        ).scalar() or 0

        return ResourceCollaborationResponse(
            total_linked_resources=total_linked,
            by_type=res_dict,
            commented_resources=commented_count
        )

    def get_top_contributors(self, workspace_id: uuid.UUID, limit: int = 10) -> TopContributorsResponse:
        rows = self.db.query(
            User.id,
            User.username,
            func.count(distinct(ActivityLog.id)).label("act_count"),
            func.count(distinct(Comment.id)).label("comm_count")
        ).join(
            WorkspaceMember, WorkspaceMember.user_id == User.id
        ).outerjoin(
            ActivityLog, ActivityLog.user_id == User.id
        ).outerjoin(
            Comment, (Comment.author_id == User.id) & (Comment.workspace_id == workspace_id)
        ).filter(
            WorkspaceMember.workspace_id == workspace_id
        ).group_by(User.id, User.username).order_by(
            func.count(distinct(ActivityLog.id)).desc(),
            User.id.asc()
        ).limit(limit).all()

        items = [
            TopContributorItem(
                user_id=r[0],
                username=r[1],
                activity_count=r[2] or 0,
                comment_count=r[3] or 0,
                mention_count=0
            )
            for r in rows
        ]

        return TopContributorsResponse(contributors=items)
