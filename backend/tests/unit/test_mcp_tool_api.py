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

    org = Organization(id=uuid.uuid4(), name="Tool Org")
    role = Role(id=uuid.uuid4(), name="User")
    db.add_all([org, role])
    db.commit()

    u1 = User(
        id=USER_1_ID,
        email="tenant1@aegis.ai",
        username="tenant1",
        password_hash="pw",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(WS_1_ID)}
    )
    u2 = User(
        id=USER_2_ID,
        email="tenant2@aegis.ai",
        username="tenant2",
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
        name="Workspace 1 Hub",
        server_url="http://localhost:8000/sse",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db.add(server1)
    db.commit()

    tool1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="analytics_runner",
        description="Run analytical computations",
        input_schema={"type": "object", "properties": {"metric": {"type": "string"}}},
        enabled=True,
        is_stale=False
    )
    tool2 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="shell_executor",
        description="Execute shell commands on server",
        enabled=True,
        is_stale=False
    )
    db.add_all([tool1, tool2])
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

def test_tool_catalog_api_flow(client):
    global current_test_user
    db = TestSessionLocal()
    u1 = db.query(User).filter_by(id=USER_1_ID).first()
    u2 = db.query(User).filter_by(id=USER_2_ID).first()
    db.close()

    current_test_user = u1

    # 1. List Workspace Tools
    list_res = client.get("/api/v1/mcp/tools")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 2
    assert len(data["tools"]) == 2

    # Check risk classification returned in API
    analytics_tool = next(t for t in data["tools"] if t["name"] == "analytics_runner")
    shell_tool = next(t for t in data["tools"] if t["name"] == "shell_executor")
    assert analytics_tool["risk_level"] == "safe"
    assert analytics_tool["available_for_execution"] is True
    assert shell_tool["risk_level"] == "restricted"

    # 2. Search Tools
    search_res = client.post("/api/v1/mcp/tools/search", json={"query": "analytics", "limit": 10})
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] >= 1
    assert search_data["results"][0]["name"] == "analytics_runner"

    # 3. Get Tool Details
    tool_id = analytics_tool["id"]
    get_res = client.get(f"/api/v1/mcp/tools/{tool_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "analytics_runner"

    # 4. Disable Tool
    dis_res = client.post(f"/api/v1/mcp/tools/{tool_id}/disable")
    assert dis_res.status_code == 200
    assert dis_res.json()["enabled"] is False
    assert dis_res.json()["available_for_execution"] is False

    # 5. Re-enable Tool
    en_res = client.post(f"/api/v1/mcp/tools/{tool_id}/enable")
    assert en_res.status_code == 200
    assert en_res.json()["enabled"] is True

    # 6. Tenant Isolation Check: User 2 from Workspace 2 cannot see or access User 1's tools
    current_test_user = u2
    u2_list_res = client.get("/api/v1/mcp/tools")
    assert u2_list_res.status_code == 200
    assert u2_list_res.json()["total"] == 0

    u2_get_res = client.get(f"/api/v1/mcp/tools/{tool_id}")
    assert u2_get_res.status_code == 404
