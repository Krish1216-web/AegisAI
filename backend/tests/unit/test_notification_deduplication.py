import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.notification import NotificationService

@pytest.fixture
def notif_dedup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Dedup Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Dedup Workspace")
    user1 = User(id=uuid.uuid4(), email="dedup1@test.com", username="dedup1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="dedup2@test.com", username="dedup2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session, ws, user1, user2
    session.close()

def test_notification_duplicate_suppression(notif_dedup_db):
    session, ws, user1, user2 = notif_dedup_db
    service = NotificationService(session)
    
    proj_id = uuid.uuid4()
    # 1. First event
    n1 = service.create_notification(
        workspace_id=ws.id,
        recipient_user_id=user2.id,
        actor_user_id=user1.id,
        type="PROJECT_MEMBER_ADDED",
        title="Added to Project",
        body="You were added",
        project_id=proj_id
    )
    
    # 2. Duplicate event within 60s
    n2 = service.create_notification(
        workspace_id=ws.id,
        recipient_user_id=user2.id,
        actor_user_id=user1.id,
        type="PROJECT_MEMBER_ADDED",
        title="Added to Project",
        body="You were added",
        project_id=proj_id
    )
    
    assert n1.id == n2.id
    assert service.get_unread_count(ws.id, user2.id) == 1
