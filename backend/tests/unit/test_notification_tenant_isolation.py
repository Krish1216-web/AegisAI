import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.notification import NotificationService

@pytest.fixture
def notif_iso_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Iso Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS B")
    user_a = User(id=uuid.uuid4(), email="usera@notif.com", username="usera", password_hash="h", role_id=user_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="userb@notif.com", username="userb", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_a, ws_b, user_a, user_b])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner"))
    session.commit()
    user_a.role = user_role
    user_b.role = user_role
    
    yield session, ws_a, ws_b, user_a, user_b
    session.close()

def test_cross_tenant_notification_isolation(notif_iso_db):
    session, ws_a, ws_b, user_a, user_b = notif_iso_db
    service = NotificationService(session)
    
    # Create notification in Workspace A for User A
    service.create_notification(
        workspace_id=ws_a.id,
        recipient_user_id=user_a.id,
        actor_user_id=None,
        type="PROJECT_MEMBER_ADDED",
        title="Welcome",
        body="Welcome to A"
    )
    
    # Query under Workspace B context for User B
    res_b = service.list_notifications(workspace_id=ws_b.id, user_id=user_b.id)
    assert res_b.total == 0
    assert service.get_unread_count(ws_b.id, user_b.id) == 0
