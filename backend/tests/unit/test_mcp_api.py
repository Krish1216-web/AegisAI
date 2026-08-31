import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.database.redis import get_redis
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember

# Setup Test Database
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestSessionLocal = sessionmaker(bind=test_engine)

MOCK_USER_ID = uuid.uuid4()
MOCK_WS_ID = uuid.uuid4()

def mock_get_current_user():
    role = Role(id=uuid.uuid4(), name="User")
    user = User(
        id=MOCK_USER_ID,
        email="mcp_tester@aegis.ai",
        username="mcp_tester",
        password_hash="pw",
        is_active=True,
        role=role,
        settings={"default_workspace_id": str(MOCK_WS_ID)}
    )
    return user

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_redis():
    class MockRedis:
        async def ping(self): return True
        async def set(self, key, val, ex=None, nx=None): return True
        async def delete(self, key): return True
    return MockRedis()

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db.add(org)
    db.commit()
    
    role = Role(id=uuid.uuid4(), name="User")
    db.add(role)
    db.commit()
    
    user = User(
        id=MOCK_USER_ID,
        email="mcp_tester@aegis.ai",
        username="mcp_tester",
        password_hash="pw",
        is_active=True,
        role_id=role.id,
        settings={"default_workspace_id": str(MOCK_WS_ID)}
    )
    ws = Workspace(
        id=MOCK_WS_ID,
        organization_id=org.id,
        name="MCP Workspace"
    )
    db.add_all([user, ws])
    db.commit()
    
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=MOCK_WS_ID,
        user_id=MOCK_USER_ID,
        role="admin"
    )
    db.add(member)
    db.commit()
    db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_rate_limit] = lambda: True
    app.dependency_overrides[get_redis] = override_get_redis
    
    yield
    
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    return TestClient(app, base_url="http://localhost")

def test_mcp_api_crud_and_discovery_e2e(client):
    # 1. Register Server
    create_payload = {
        "name": "Integration Test Server",
        "server_url": "mock://test-api",
        "transport": "sse",
        "description": "Mock server for API tests",
        "authentication_type": "api_key",
        "auth_config": {"api_key": "sk-test-secret-12345"},
        "metadata": {"env": "test"}
    }
    create_res = client.post("/api/v1/mcp/servers", json=create_payload)
    assert create_res.status_code == 201
    server_data = create_res.json()
    server_id = server_data["id"]
    assert server_data["name"] == "Integration Test Server"
    assert "••••" in server_data["auth_config"]["api_key"]  # Verify credentials masked in API
    
    # 2. List Servers
    list_res = client.get("/api/v1/mcp/servers")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(s["id"] == server_id for s in list_data["servers"])
    
    # 3. Get Server
    get_res = client.get(f"/api/v1/mcp/servers/{server_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == server_id
    
    # 4. Patch Server
    patch_payload = {"description": "Updated mock description"}
    patch_res = client.patch(f"/api/v1/mcp/servers/{server_id}", json=patch_payload)
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated mock description"
    
    # 5. Health Check Probe Endpoint
    health_res = client.get(f"/api/v1/mcp/servers/{server_id}/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["is_healthy"] is True
    assert health_data["latency_ms"] is not None

    # 6. Discover / Refresh Capabilities Endpoint
    disc_res = client.post(f"/api/v1/mcp/servers/{server_id}/refresh")
    assert disc_res.status_code == 200
    disc_data = disc_res.json()
    assert disc_data["total_tools"] == 3
    assert disc_data["status"] == "active"
    assert disc_data["tools_added"] == 3
    
    # 7. List Capabilities
    caps_res = client.get(f"/api/v1/mcp/servers/{server_id}/capabilities")
    assert caps_res.status_code == 200
    caps_data = caps_res.json()
    assert caps_data["total"] == 7
    sample_cap_id = caps_data["capabilities"][0]["id"]

    # 8. List Specific Typed Endpoints (Tools, Resources, Prompts)
    tools_res = client.get(f"/api/v1/mcp/servers/{server_id}/tools")
    assert tools_res.status_code == 200
    assert tools_res.json()["total"] == 3

    resources_res = client.get(f"/api/v1/mcp/servers/{server_id}/resources")
    assert resources_res.status_code == 200
    assert resources_res.json()["total"] == 2

    prompts_res = client.get(f"/api/v1/mcp/servers/{server_id}/prompts")
    assert prompts_res.status_code == 200
    assert prompts_res.json()["total"] == 2

    # 9. Get Single Capability Details
    cap_detail_res = client.get(f"/api/v1/mcp/capabilities/{sample_cap_id}")
    assert cap_detail_res.status_code == 200
    assert cap_detail_res.json()["id"] == sample_cap_id
    assert cap_detail_res.json()["version"] == 1
    
    # 10. Disable & Enable Server
    dis_res = client.post(f"/api/v1/mcp/servers/{server_id}/disable")
    assert dis_res.status_code == 200
    assert dis_res.json()["enabled"] is False
    
    en_res = client.post(f"/api/v1/mcp/servers/{server_id}/enable")
    assert en_res.status_code == 200
    assert en_res.json()["enabled"] is True
    
    # 11. Delete Server
    del_res = client.delete(f"/api/v1/mcp/servers/{server_id}")
    assert del_res.status_code == 204
    
    # 12. Verify 404 after delete
    get_404 = client.get(f"/api/v1/mcp/servers/{server_id}")
    assert get_404.status_code == 404
