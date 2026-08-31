import pytest
import uuid
import json
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_resource_service import MCPResourceService
from app.core.mcp.validation import MCPValidator
from app.core.mcp.base import MCPValidationError
from app.core.agent.critic import CriticAgent
from app.core.agent.base import ExecutionContext
from app.services.ai_service import AIService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Res Sec Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    u1 = User(id=uuid.uuid4(), email="rsec1@test.com", username="rsec1", password_hash="pw", role_id=role.id, is_active=True)
    u2 = User(id=uuid.uuid4(), email="rsec2@test.com", username="rsec2", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS RSec 1")
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS RSec 2")
    session.add_all([u1, u2, ws1, ws2])
    session.commit()
    
    yield session
    session.close()

def test_resource_uri_security_rules():
    # 1. Path traversal
    with pytest.raises(MCPValidationError) as exc1:
        MCPValidator.validate_resource_uri("workspace://../secrets/config.json")
    assert "path traversal" in str(exc1.value).lower()

    # 2. Local file:// scheme
    with pytest.raises(MCPValidationError) as exc2:
        MCPValidator.validate_resource_uri("file:///etc/passwd")
    assert "file://" in str(exc2.value).lower()

    # 3. SSRF Localhost / Loopback
    with pytest.raises(MCPValidationError) as exc3:
        MCPValidator.validate_resource_uri("http://127.0.0.1/admin/debug")
    assert "prohibited" in str(exc3.value).lower()

    # 4. SSRF Cloud Metadata
    with pytest.raises(MCPValidationError) as exc4:
        MCPValidator.validate_resource_uri("http://169.254.169.254/latest/meta-data")
    assert "prohibited" in str(exc4.value).lower()

    # 5. Embedded credentials
    with pytest.raises(MCPValidationError) as exc5:
        MCPValidator.validate_resource_uri("https://admin:supersecret@example.com/api/data")
    assert "embedded credentials" in str(exc5.value).lower()

    # 6. Valid custom schemes
    assert MCPValidator.validate_resource_uri("workspace://models/weights.bin") == "workspace://models/weights.bin"
    assert MCPValidator.validate_resource_uri("db://analytics/sales_q3") == "db://analytics/sales_q3"

@pytest.mark.asyncio
async def test_resource_tenant_isolation(db_session):
    u1 = db_session.query(User).filter_by(email="rsec1@test.com").first()
    u2 = db_session.query(User).filter_by(email="rsec2@test.com").first()
    ws1 = db_session.query(Workspace).filter_by(name="WS RSec 1").first()
    ws2 = db_session.query(Workspace).filter_by(name="WS RSec 2").first()

    server1 = MCPServer(
        id=uuid.uuid4(),
        user_id=u1.id,
        workspace_id=ws1.id,
        name="Server 1",
        server_url="mock://s1",
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server1)
    db_session.commit()

    res1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="Confidential Resource",
        input_schema={"uri": "workspace://secret/doc.md"},
        enabled=True,
        is_stale=False
    )
    db_session.add(res1)
    db_session.commit()

    service = MCPResourceService(db_session)

    # User 2 / Workspace 2 cannot find or read User 1's resource
    assert service.get_resource(u2.id, ws2.id, res1.id) is None
    with pytest.raises(MCPValidationError):
        await service.read_resource(u2.id, ws2.id, res1.id)

@pytest.mark.asyncio
async def test_critic_rejects_fabricated_and_cross_tenant_mcp_citations():
    mock_ai = MagicMock(spec=AIService)
    critic = CriticAgent(mock_ai)
    context = ExecutionContext(
        request_id="req-1",
        user_id="u1",
        workspace_id="ws-B",
        conversation_id="conv-1",
        model="gpt-4o",
        provider="mock"
    )

    # 1. Fabricated MCP citation
    state_fab = {
        "original_prompt": "analyze data",
        "agent_outputs": {},
        "mcp_citations": [{"source_type": "mcp_resource", "resource_id": "fabricated-res-999"}]
    }
    res_fab = await critic.execute(state_fab, context)
    assert res_fab.status == "failed"
    assert json.loads(res_fab.output)["decision"] == "FAIL"

    # 2. Cross-tenant MCP citation
    state_cross = {
        "original_prompt": "analyze data",
        "agent_outputs": {},
        "mcp_citations": [{"source_type": "mcp_resource", "resource_id": "res-1", "server_id": "tenant-a-server"}]
    }
    res_cross = await critic.execute(state_cross, context)
    assert res_cross.status == "failed"
    assert json.loads(res_cross.output)["decision"] == "FAIL"
