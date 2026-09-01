import uuid
import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team
from app.models.project import Project
from app.models.comment import Comment
from app.models.audit import ActivityLog
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_overview_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Analytics Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Analytics Workspace")
    user1 = User(id=uuid.uuid4(), email="user1@analytics.com", username="user1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="user2@analytics.com", username="user2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    
    # Add team & project
    t = Team(id=uuid.uuid4(), workspace_id=ws.id, name="Analytics Team", created_by=user1.id, status="active")
    p = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Analytics Proj", created_by=user1.id, status="active")
    session.add_all([t, p])
    session.flush()
    
    # Add comment & activity
    c = Comment(id=uuid.uuid4(), workspace_id=ws.id, project_id=p.id, author_id=user1.id, body="First comment")
    act = ActivityLog(id=uuid.uuid4(), user_id=user1.id, activity_type="COMMENT_CREATE", description="User created a comment")
    session.add_all([c, act])
    session.commit()
    
    yield session, ws, user1, user2
    session.close()

def test_collaboration_overview_metrics(collab_overview_db):
    session, ws, user1, user2 = collab_overview_db
    service = CollaborationAnalyticsService(session)
    
    overview = service.get_overview(workspace_id=ws.id, time_window="7d")
    assert overview.workspace_id == ws.id
    assert overview.total_members == 2
    assert overview.active_teams == 1
    assert overview.active_projects == 1
    assert overview.total_comments == 1
    assert overview.root_comments == 1
    assert overview.total_replies == 0
    assert overview.total_activities == 1
    assert overview.active_users == 1
    assert overview.engagement_rate == 0.5
    assert overview.health_status == "HEALTHY"
