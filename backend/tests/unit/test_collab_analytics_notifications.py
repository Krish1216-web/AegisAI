import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.notification import Notification
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_notif_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Notif Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Notif Workspace")
    user = User(id=uuid.uuid4(), email="nuser@test.com", username="nuser", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user])
    session.flush()
    
    n1 = Notification(id=uuid.uuid4(), workspace_id=ws.id, recipient_user_id=user.id, type="MENTION", title="M1", body="B1", status="read")
    n2 = Notification(id=uuid.uuid4(), workspace_id=ws.id, recipient_user_id=user.id, type="MENTION", title="M2", body="B2", status="unread")
    session.add_all([n1, n2])
    session.commit()
    
    yield session, ws
    session.close()

def test_notification_analytics_read_rate(collab_notif_db):
    session, ws = collab_notif_db
    service = CollaborationAnalyticsService(session)
    
    res = service.get_notification_analytics(workspace_id=ws.id)
    assert res.total_generated == 2
    assert res.total_read == 1
    assert res.total_unread == 1
    assert res.read_rate == 0.5
    assert res.by_type.get("MENTION") == 2
