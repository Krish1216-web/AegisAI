import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_zero_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Zero Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Empty Workspace")
    session.add(ws)
    session.commit()
    
    yield session, ws
    session.close()

def test_zero_division_guardrails(collab_zero_db):
    session, ws = collab_zero_db
    service = CollaborationAnalyticsService(session)
    
    # Test completely empty workspace
    overview = service.get_overview(workspace_id=ws.id)
    assert overview.engagement_rate == 0.0
    assert overview.health_status == "LOW"
    assert overview.activity_growth.growth_rate == 0.0
    assert overview.comment_growth.growth_rate == 0.0
    
    comm = service.get_comment_analytics(workspace_id=ws.id)
    assert comm.reply_to_root_ratio == 0.0
    assert comm.avg_comments_per_project == 0.0
    
    notif = service.get_notification_analytics(workspace_id=ws.id)
    assert notif.read_rate == 0.0
