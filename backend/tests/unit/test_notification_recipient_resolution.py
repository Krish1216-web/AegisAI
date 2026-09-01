import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.notification import NotificationService

@pytest.fixture
def notif_recipient_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Recipient Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Recipient Workspace")
    user1 = User(id=uuid.uuid4(), email="rec1@notif.com", username="rec1", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.commit()
    user1.role = user_role
    
    yield session, ws, user1
    session.close()

def test_self_notification_prevention(notif_recipient_db):
    session, ws, user1 = notif_recipient_db
    service = NotificationService(session)
    
    # Self notification where actor == recipient -> returns None
    notif = service.create_notification(
        workspace_id=ws.id,
        recipient_user_id=user1.id,
        actor_user_id=user1.id,
        type="MENTION",
        title="Self mention",
        body="You mentioned yourself"
    )
    assert notif is None
    assert service.get_unread_count(ws.id, user1.id) == 0
