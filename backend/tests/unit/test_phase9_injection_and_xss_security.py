import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership
from app.services.comment import CommentService
from app.core.email.provider import MockEmailProvider

@pytest.fixture
def injection_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Injection Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Injection Workspace")
    user = User(id=uuid.uuid4(), email="attacker@test.com", username="attacker", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user])
    session.flush()

    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner"))
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Injection Project", created_by=user.id, status="active")
    session.add(proj)
    session.flush()

    session.add(ProjectMembership(id=uuid.uuid4(), project_id=proj.id, user_id=user.id, role="owner", status="active"))
    session.commit()
    user.role = user_role

    yield session, ws, user, proj
    session.close()

def test_sql_and_xss_injection_handling(injection_db):
    session, ws, user, proj = injection_db
    service = CommentService(session)

    # XSS payload in comment body
    xss_payload = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
    comment = service.create_comment(
        workspace_id=ws.id,
        author_id=user.id,
        project_id=proj.id,
        body=xss_payload
    )
    assert comment.body == xss_payload

    # Email provider sanitization check
    provider = MockEmailProvider()
    provider.send_email(
        to_email="test@example.com",
        subject="Alert <script>",
        body_text="Body with <img onerror>"
    )
    assert len(provider.sent_emails) == 1
    sent = provider.sent_emails[0]
    assert "<script>" not in sent["subject"]
    assert "&lt;script&gt;" in sent["subject"]
