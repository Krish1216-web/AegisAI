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
USER_2_ID = uuid.uuid4()
WS_2_ID = uuid.uuid4()

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

    org = Organization(id=uuid.uuid4(), name="API Exec Org")
    role = Role(id=uuid.uuid4(), name="User")
    db.add_all([org, role])
    db.commit()

    u1 = User(
        id=USER_1_ID,
        email="api_exec1@aegis.ai",
        username="api_exec1",
        password_hash="pw",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(WS_1_ID)}
    )
    u2 = User(
        id=USER_2_ID,
        email="api_exec2@aegis.ai",
        username="api_exec2",
        password_hash="pw",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(WS_2_ID)}
    )
    ws1 = Workspace(id=WS_1_ID, organization_id=org.id, name="WS 1")
    ws2 = Workspace(id=WS_2_ID, organization_id=org.id, name="WS 2")
    db.add_all([u1, u2, ws1, ws2])
    db.commit()

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_1_ID, user_id=USER_1_ID, role="admin")
    m2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_2_ID, user_id=USER_2_ID, role="admin")
    db.add_all([m1, m2])
    db.commit()

    # Seed MCP Server & Tools for Workspace 1
    server1 = MCPServer(
        id=uuid.uuid4(),
        user_id=USER_1_ID,
        workspace_id=WS_1_ID,
        name="Server 1",
        server_url="mock://api-test",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db.add(server1)
    db.commit()

    # Safe tool
    safe_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        description="Calculate addition",
        input_schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        enabled=True,
        is_stale=False
    )
    # Restricted tool
    restr_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="execute_shell_command",
        description="Run bash command",
        input_schema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        enabled=True,
        is_stale=False
    )
    db.add_all([safe_tool, restr_tool])
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

def test_api_tool_execution_endpoints(client):
    global current_test_user
    db = TestSessionLocal()
    u1 = db.query(User).filter_by(id=USER_1_ID).first()
    u2 = db.query(User).filter_by(id=USER_2_ID).first()
    safe_t = db.query(MCPCapability).filter_by(name="calculate_sum").first()
    restr_t = db.query(MCPCapability).filter_by(name="execute_shell_command").first()
    db.close()

    current_test_user = u1

    # 1. Execute Safe Tool
    res_safe = client.post(
        f"/api/v1/mcp/tools/{safe_t.id}/execute",
        json={"arguments": {"a": 20, "b": 30}}
    )
    assert res_safe.status_code == 200
    safe_data = res_safe.json()
    assert safe_data["status"] == "SUCCESS"
    assert safe_data["result"]["sum"] == 50

    # 2. Execute Restricted Tool without confirmation -> 428 Precondition Required
    res_restr = client.post(
        f"/api/v1/mcp/tools/{restr_t.id}/execute",
        json={"arguments": {"command": "uptime"}}
    )
    assert res_restr.status_code == 428
    assert "REQUIRES_CONFIRMATION" in str(res_restr.json())

    # 3. Generate confirmation token for restricted tool
    conf_res = client.post(
        f"/api/v1/mcp/tools/{restr_t.id}/confirm",
        json={"arguments": {"command": "uptime"}}
    )
    assert conf_res.status_code == 200
    conf_token = conf_res.json()["token"]
    assert conf_token is not None

    # 4. Execute Restricted Tool with confirmation token -> 200 Success
    res_confirmed = client.post(
        f"/api/v1/mcp/tools/{restr_t.id}/execute",
        json={"arguments": {"command": "uptime"}, "confirmation_token": conf_token}
    )
    assert res_confirmed.status_code == 200
    assert res_confirmed.json()["status"] == "SUCCESS"

    # 5. Multi-Tenant Check: User 2 cannot execute User 1's tools
    current_test_user = u2
    res_cross = client.post(
        f"/api/v1/mcp/tools/{safe_t.id}/execute",
        json={"arguments": {"a": 1, "b": 2}}
    )
    assert res_cross.status_code == 400 or res_cross.status_code == 404
