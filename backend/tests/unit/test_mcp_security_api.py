import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPServerStatus, MCPTransport

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestSessionLocal = sessionmaker(bind=test_engine)

USER_1_ID = uuid.uuid4()
WS_1_ID = uuid.uuid4()

current_test_user = None

def mock_get_current_user():
    return current_test_user

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    global current_test_user
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()

    org = Organization(id=uuid.uuid4(), name="API Security Org")
    role = Role(id=uuid.uuid4(), name="User")
    db.add_all([org, role])
    db.commit()

    u1 = User(
        id=USER_1_ID,
        email="api_sec1@aegis.ai",
        username="api_sec1",
        password_hash="pw",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(WS_1_ID)}
    )
    ws1 = Workspace(id=WS_1_ID, organization_id=org.id, name="WS Sec API")
    db.add_all([u1, ws1])
    db.commit()

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_1_ID, user_id=USER_1_ID, role="admin")
    db.add(m1)
    db.commit()

    server1 = MCPServer(
        id=uuid.uuid4(),
        user_id=USER_1_ID,
        workspace_id=WS_1_ID,
        name="Server Sec API",
        server_url="mock://api-sec-test",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db.add(server1)
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_rate_limit] = lambda: True

    current_test_user = u1

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    return TestClient(app, base_url="http://localhost")

def test_api_security_status_and_audit_endpoints(client):
    global current_test_user
    db = TestSessionLocal()
    u1 = db.query(User).filter_by(id=USER_1_ID).first()
    db.close()

    current_test_user = u1

    # 1. GET /api/v1/mcp/security/status
    res_status = client.get("/api/v1/mcp/security/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["policy_engine_active"] is True
    assert data["confirmation_gate_active"] is True
    assert data["ssrf_defense_active"] is True
    assert data["total_servers"] == 1
    assert "mcp:tool:execute" in data["active_permissions"]

    # 2. GET /api/v1/mcp/security/audit-log
    res_audit = client.get("/api/v1/mcp/security/audit-log?limit=10")
    assert res_audit.status_code == 200
    assert "events" in res_audit.json()
    assert "total" in res_audit.json()
