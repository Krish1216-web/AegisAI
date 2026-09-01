import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.notification import NotificationService

@pytest.fixture
def notif_pref_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Pref Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Pref Workspace")
    user1 = User(id=uuid.uuid4(), email="pref1@test.com", username="pref1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="pref2@test.com", username="pref2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session, ws, user1, user2
    session.close()

def test_notification_preference_toggling(notif_pref_db):
    session, ws, user1, user2 = notif_pref_db
    service = NotificationService(session)
    
    # Disable in-app and email for MENTION for user2
    service.update_preference(user2.id, "MENTION", in_app_enabled=False, email_enabled=False)
    
    # User1 mentions User2 -> should be skipped because of preference
    n = service.create_notification(
        workspace_id=ws.id,
        recipient_user_id=user2.id,
        actor_user_id=user1.id,
        type="MENTION",
        title="Mentioned",
        body="@pref2 check"
    )
    assert n is None
    assert service.get_unread_count(ws.id, user2.id) == 0
