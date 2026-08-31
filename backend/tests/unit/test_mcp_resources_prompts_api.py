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

    org = Organization(id=uuid.uuid4(), name="API RP Org")
    role = Role(id=uuid.uuid4(), name="User")
    db.add_all([org, role])
    db.commit()

    u1 = User(
        id=USER_1_ID,
        email="api_rp1@aegis.ai",
        username="api_rp1",
        password_hash="pw",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(WS_1_ID)}
    )
    u2 = User(
        id=USER_2_ID,
        email="api_rp2@aegis.ai",
        username="api_rp2",
        password_hash="pw",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(WS_2_ID)}
    )
    ws1 = Workspace(id=WS_1_ID, organization_id=org.id, name="WS RP 1")
    ws2 = Workspace(id=WS_2_ID, organization_id=org.id, name="WS RP 2")
    db.add_all([u1, u2, ws1, ws2])
    db.commit()

    m1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_1_ID, user_id=USER_1_ID, role="admin")
    m2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_2_ID, user_id=USER_2_ID, role="admin")
    db.add_all([m1, m2])
    db.commit()

    # Seed MCP Server with Resource & Prompt for Workspace 1
    server1 = MCPServer(
        id=uuid.uuid4(),
        user_id=USER_1_ID,
        workspace_id=WS_1_ID,
        name="Server 1 RP",
        server_url="mock://api-rp-test",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db.add(server1)
    db.commit()

    resource1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="Docs Architecture",
        description="Architecture guide",
        input_schema={"uri": "workspace://docs/architecture.md", "mime_type": "text/markdown"},
        enabled=True,
        is_stale=False
    )
    prompt1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.PROMPT,
        name="audit_code_security",
        description="Security analysis",
        input_schema={"arguments": [{"name": "code", "required": True}]},
        enabled=True,
        is_stale=False
    )
    db.add_all([resource1, prompt1])
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

def test_api_resources_and_prompts_crud_and_execution(client):
    global current_test_user
    db = TestSessionLocal()
    u1 = db.query(User).filter_by(id=USER_1_ID).first()
    u2 = db.query(User).filter_by(id=USER_2_ID).first()
    res1 = db.query(MCPCapability).filter_by(name="Docs Architecture").first()
    prompt1 = db.query(MCPCapability).filter_by(name="audit_code_security").first()
    db.close()

    current_test_user = u1

    # 1. List Resources
    res_list = client.get("/api/v1/mcp/resources")
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1
    assert res_list.json()["resources"][0]["name"] == "Docs Architecture"

    # 2. Search Resources
    res_search = client.post("/api/v1/mcp/resources/search", json={"query": "Docs"})
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1

    # 3. Read Resource
    res_read = client.post(f"/api/v1/mcp/resources/{res1.id}/read")
    assert res_read.status_code == 200
    assert res_read.json()["uri"] == "workspace://docs/architecture.md"
    assert "# AegisAI Architecture" in res_read.json()["text"]

    # 4. List Prompts
    p_list = client.get("/api/v1/mcp/prompts")
    assert p_list.status_code == 200
    assert p_list.json()["total"] == 1

    # 5. Search Prompts
    p_search = client.post("/api/v1/mcp/prompts/search", json={"query": "audit"})
    assert p_search.status_code == 200
    assert p_search.json()["total"] == 1

    # 6. Render Prompt
    p_render = client.post(
        f"/api/v1/mcp/prompts/{prompt1.id}/render",
        json={"arguments": {"code": "x = 10"}}
    )
    assert p_render.status_code == 200
    assert p_render.json()["name"] == "audit_code_security"
    assert p_render.json()["untrusted"] is True

    # 7. Multi-Tenant Check: User 2 cannot access User 1's resource or prompt
    current_test_user = u2
    res_cross = client.post(f"/api/v1/mcp/resources/{res1.id}/read")
    assert res_cross.status_code == 400 or res_cross.status_code == 404

    prompt_cross = client.post(f"/api/v1/mcp/prompts/{prompt1.id}/render", json={"arguments": {"code": "x = 10"}})
    assert prompt_cross.status_code == 400 or prompt_cross.status_code == 404
