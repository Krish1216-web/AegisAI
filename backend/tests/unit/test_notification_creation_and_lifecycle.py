import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project
from app.services.notification import NotificationService

@pytest.fixture
def notif_lifecycle_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Notif Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Notif Workspace")
    user1 = User(id=uuid.uuid4(), email="user1@notif.com", username="user1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="user2@notif.com", username="user2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session, ws, user1, user2
    session.close()

def test_notification_creation_read_and_mark_all(notif_lifecycle_db):
    session, ws, user1, user2 = notif_lifecycle_db
    service = NotificationService(session)
    
    # 1. User1 creates notification for User2
    n = service.create_notification(
        workspace_id=ws.id,
        recipient_user_id=user2.id,
        actor_user_id=user1.id,
        type="MENTION",
        title="Mentioned you",
        body="@user2 check this out"
    )
    assert n is not None
    assert n.status == "unread"
    
    # 2. Check unread count
    assert service.get_unread_count(ws.id, user2.id) == 1
    
    # 3. Mark single as read
    read_n = service.mark_as_read(ws.id, user2.id, n.id)
    assert read_n.status == "read"
    assert read_n.read_at is not None
    assert service.get_unread_count(ws.id, user2.id) == 0
