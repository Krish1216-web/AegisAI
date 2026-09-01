import uuid
import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.audit import ActivityLog
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_act_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Act Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Act Workspace")
    user = User(id=uuid.uuid4(), email="actuser@test.com", username="actuser", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user])
    session.flush()
    
    act1 = ActivityLog(id=uuid.uuid4(), user_id=user.id, activity_type="COMMENT_CREATE", description="Commented")
    act2 = ActivityLog(id=uuid.uuid4(), user_id=user.id, activity_type="PROJECT_CREATE", description="Created Project")
    session.add_all([act1, act2])
    session.commit()
    
    yield session, ws
    session.close()

def test_activity_time_series_aggregation(collab_act_db):
    session, ws = collab_act_db
    service = CollaborationAnalyticsService(session)
    
    res = service.get_activity_time_series(workspace_id=ws.id, time_window="7d")
    assert res.total_activities == 2
    assert len(res.series) >= 1
    assert res.series[0].count == 2
