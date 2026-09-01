import uuid
import pytest
from app.core.email.provider import MockEmailProvider, set_email_provider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.notification import NotificationService

@pytest.fixture
def notif_email_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Email Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Email Workspace")
    user1 = User(id=uuid.uuid4(), email="email1@test.com", username="email1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="email2@test.com", username="email2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session, ws, user1, user2
    session.close()

def test_email_dispatch_and_escaping(notif_email_db):
    session, ws, user1, user2 = notif_email_db
    mock_provider = MockEmailProvider()
    set_email_provider(mock_provider)
    
    service = NotificationService(session)
    
    # Create notification with HTML/script characters to test sanitization
    service.create_notification(
        workspace_id=ws.id,
        recipient_user_id=user2.id,
        actor_user_id=user1.id,
        type="MENTION",
        title="Mentioned <script>alert(1)</script>",
        body="Hello @email2 & welcome!"
    )
    
    assert len(mock_provider.sent_emails) == 1
    sent = mock_provider.sent_emails[0]
    assert sent["to"] == "email2@test.com"
    assert "<script>" not in sent["subject"]
    assert "&lt;script&gt;" in sent["subject"]
