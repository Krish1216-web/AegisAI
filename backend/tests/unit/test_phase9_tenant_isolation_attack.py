import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.project import Project, ProjectMembership
from app.models.comment import Comment
from app.models.notification import Notification
from app.services.comment import CommentService
from app.services.notification import NotificationService
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def tenant_attack_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Attack Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace B")
    user_a = User(id=uuid.uuid4(), email="alice@a.com", username="alice", password_hash="h", role_id=user_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="bob@b.com", username="bob", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_a, ws_b, user_a, user_b])
    session.flush()

    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner"))

    team_b = Team(id=uuid.uuid4(), workspace_id=ws_b.id, name="Team B", created_by=user_b.id, status="active")
    proj_b = Project(id=uuid.uuid4(), workspace_id=ws_b.id, name="Proj B", created_by=user_b.id, status="active")
    session.add_all([team_b, proj_b])
    session.flush()

    session.add(TeamMembership(id=uuid.uuid4(), team_id=team_b.id, user_id=user_b.id, role="owner"))
    session.add(ProjectMembership(id=uuid.uuid4(), project_id=proj_b.id, user_id=user_b.id, role="owner", status="active"))

    comm_b = Comment(id=uuid.uuid4(), workspace_id=ws_b.id, project_id=proj_b.id, author_id=user_b.id, body="Secret in B")
    notif_b = Notification(id=uuid.uuid4(), workspace_id=ws_b.id, recipient_user_id=user_b.id, type="MENTION", title="Alert B", body="Private B", status="unread")
    session.add_all([comm_b, notif_b])
    session.commit()

    user_a.role = user_role
    user_b.role = user_role

    yield session, ws_a, ws_b, user_a, user_b, team_b, proj_b
    session.close()

def test_cross_tenant_isolation_attacks(tenant_attack_db):
    session, ws_a, ws_b, user_a, user_b, team_b, proj_b = tenant_attack_db

    # 1. Alice (in WS A) attempts to list comments in Project B (WS B)
    comment_service = CommentService(session)
    res_comments = comment_service.list_comments(workspace_id=ws_a.id, project_id=proj_b.id)
    assert res_comments.total == 0

    # 2. Alice attempts to query notifications for WS B
    notif_service = NotificationService(session)
    res_notifs = notif_service.list_notifications(workspace_id=ws_a.id, user_id=user_a.id)
    assert res_notifs.total == 0

    # 3. Alice queries collaboration analytics for WS A -> Should not see WS B's project
    analytics_service = CollaborationAnalyticsService(session)
    res_analytics = analytics_service.get_overview(workspace_id=ws_a.id)
    assert res_analytics.active_projects == 0
    assert res_analytics.total_comments == 0
