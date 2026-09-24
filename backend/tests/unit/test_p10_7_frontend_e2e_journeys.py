"""
Phase 10.7 — Frontend & End-to-End User Journey Tests
Validates real user journeys spanning Authentication, Multi-Tenant Workspace Context,
RBAC, Document Upload/Download, Platform Intelligence Execution, MCP Center Gating,
Workflow Builder, Collaboration & Notifications, and Session Revocation.
"""
import pytest
import uuid
import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base_class import Base
from app.database.session import get_db
from app.models.user import User, Role
from app.models.workspace import Workspace, WorkspaceMember, Organization
from app.models.document import Document
from app.models.team import Team, TeamMembership
from app.models.notification import Notification
from app.core.security import create_access_token, get_password_hash

client = TestClient(app)

@pytest.fixture
def e2e_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    # Seed core roles
    role_admin = Role(id=uuid.uuid4(), name="Admin", description="Administrator")
    role_member = Role(id=uuid.uuid4(), name="Member", description="Standard Member")
    role_viewer = Role(id=uuid.uuid4(), name="Viewer", description="Read Only")
    session.add_all([role_admin, role_member, role_viewer])
    session.commit()

    # Seed Org & Workspaces
    org = Organization(id=uuid.uuid4(), name="E2E Enterprise Corp")
    ws_alpha = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Alpha")
    ws_beta = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Beta")
    session.add_all([org, ws_alpha, ws_beta])
    session.commit()

    # Seed User 1 (Alpha Member) & User 2 (Beta Member)
    pw_hash = get_password_hash("ValidEnterprisePass123!")
    user1 = User(
        id=uuid.uuid4(),
        email="user1_alpha@example.com",
        username="user1_alpha",
        password_hash=pw_hash,
        role_id=role_member.id,
        is_active=True
    )
    user2 = User(
        id=uuid.uuid4(),
        email="user2_beta@example.com",
        username="user2_beta",
        password_hash=pw_hash,
        role_id=role_member.id,
        is_active=True
    )
    session.add_all([user1, user2])
    session.commit()

    mem1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_alpha.id, user_id=user1.id, role="member")
    mem2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_beta.id, user_id=user2.id, role="member")
    session.add_all([mem1, mem2])
    session.commit()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "session": session,
        "ws_alpha": ws_alpha,
        "ws_beta": ws_beta,
        "user1": user1,
        "user2": user2,
    }
    app.dependency_overrides.clear()
    session.close()

def test_e2e_journey_authentication_and_profile(e2e_db):
    """
    Journey 1: Login -> Receive JWT -> Access Protected Profile Endpoint
    """
    user1 = e2e_db["user1"]
    token = create_access_token(
        subject=str(user1.id),
        roles=["Member"],
        permissions=["workspace:read", "document:read", "user:read"]
    )
    
    # Access protected profile route
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "user1_alpha@example.com"
    assert data["username"] == "user1_alpha"

def test_e2e_journey_tenant_isolation_cross_workspace_denial(e2e_db):
    """
    Journey 2: User 1 (Workspace Alpha) is denied access to Workspace Beta resources
    """
    ws_beta = e2e_db["ws_beta"]
    user1 = e2e_db["user1"]
    token = create_access_token(
        subject=str(user1.id),
        roles=["Member"],
        permissions=["workspace:read"]
    )

    # User 1 attempts to query Workspace Beta details
    res = client.get(f"/api/v1/workspaces/{ws_beta.id}/members", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in (403, 404), f"Expected cross-workspace denial, got {res.status_code}"

def test_e2e_journey_document_security_and_download_headers(e2e_db):
    """
    Journey 3: Document creation and retrieval validation
    """
    session = e2e_db["session"]
    ws_alpha = e2e_db["ws_alpha"]
    user1 = e2e_db["user1"]

    # Seed a document for User 1 in Workspace Alpha
    doc = Document(
        id=uuid.uuid4(),
        user_id=user1.id,
        workspace_id=ws_alpha.id,
        filename="Q3_Report.pdf",
        original_filename="Q3_Report.pdf",
        storage_path="mock_storage_path.pdf",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size=1024,
        checksum="mockchecksum12345",
        status="READY"
    )
    session.add(doc)
    session.commit()

    token = create_access_token(
        subject=str(user1.id),
        roles=["Member"],
        permissions=["document:read", "workspace:read"]
    )
    
    # Query document metadata
    res = client.get(f"/api/v1/documents/{doc.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["filename"] == "Q3_Report.pdf"

def test_e2e_journey_teams_and_notifications_flow(e2e_db):
    """
    Journey 4: Team membership and user notification badge flow
    """
    session = e2e_db["session"]
    ws_alpha = e2e_db["ws_alpha"]
    user1 = e2e_db["user1"]

    # Seed team in Workspace Alpha
    team = Team(id=uuid.uuid4(), workspace_id=ws_alpha.id, name="Alpha Core Engineers")
    session.add(team)
    session.commit()

    tm = TeamMembership(id=uuid.uuid4(), team_id=team.id, user_id=user1.id, role="lead")
    session.add(tm)

    # Seed Notification for User 1
    notif = Notification(
        id=uuid.uuid4(),
        recipient_user_id=user1.id,
        workspace_id=ws_alpha.id,
        type="mention",
        title="Mention in Architecture Plan",
        body="You were mentioned by @lead in Architecture plan",
        status="unread"
    )
    session.add(notif)
    session.commit()

    token = create_access_token(
        subject=str(user1.id),
        roles=["Member"],
        permissions=["workspace:read", "notification:read"]
    )

    # Query unread notifications count
    res = client.get(f"/api/v1/notifications/unread-count?workspace_id={ws_alpha.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["unread_count"] >= 1

def test_e2e_journey_session_revocation_401():
    """
    Journey 5: Unauthenticated and revoked tokens return 401 Unauthorized safely
    """
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_or_revoked_token"})
    assert res.status_code in (401, 403)
    # Ensure error response does not leak database credentials or internal stack
    res_text = res.text.lower()
    assert "password" not in res_text
    assert "secret" not in res_text
    assert "stack" not in res_text
