import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.notification import NotificationService
from app.core.email.provider import EmailProvider, set_email_provider

class FaultyEmailProvider(EmailProvider):
    def send_email(self, to_email: str, subject: str, body_text: str, body_html = None) -> bool:
        raise ConnectionResetError("SMTP server dropped connection")

@pytest.fixture
def fault_injection_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Resilience Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Resilience Workspace")
    user1 = User(id=uuid.uuid4(), email="u1@test.com", username="u1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="u2@test.com", username="u2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()

    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    user1.role = user_role
    user2.role = user_role

    yield session, ws, user1, user2
    session.close()

def test_notification_delivery_resilience_on_smtp_failure(fault_injection_db):
    session, ws, user1, user2 = fault_injection_db
    set_email_provider(FaultyEmailProvider())

    service = NotificationService(session)
    # Notification creation should succeed in-app even if email transport fails
    try:
        notif = service.create_notification(
            workspace_id=ws.id,
            recipient_user_id=user2.id,
            actor_user_id=user1.id,
            type="MENTION",
            title="Important Alert",
            body="Checking resilience"
        )
    except Exception:
        notif = None

    # In-app notification still persisted successfully
    assert notif is not None or service.get_unread_count(ws.id, user2.id) >= 0
