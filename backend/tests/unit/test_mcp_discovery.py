import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_registry import MCPRegistryService
from app.services.mcp.mcp_discovery import MCPDiscoveryService
from app.core.mcp.base import MCPValidationError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Test Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    user = User(id=uuid.uuid4(), email="user@example.com", username="user", password_hash="pw", role_id=role.id, is_active=True)
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace 1")
    session.add_all([user, ws])
    session.commit()
    
    yield session
    session.close()

@pytest.mark.asyncio
async def test_mcp_capability_discovery_sync(db_session):
    user = db_session.query(User).first()
    ws = db_session.query(Workspace).first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Mock MCP Server",
        server_url="mock://tools",
        transport=MCPTransport.SSE
    )
    
    discovery = MCPDiscoveryService(db_session)
    res = await discovery.discover_capabilities(user.id, ws.id, server.id)
    
    assert res["status"] == "active"
    assert res["total_tools"] == 3
    assert res["total_resources"] == 2
    assert res["total_prompts"] == 2
    assert res["tools_added"] == 3
    assert res["resources_added"] == 2
    assert res["prompts_added"] == 2
    
    # Check database records
    caps = db_session.query(MCPCapability).filter_by(server_id=server.id).all()
    assert len(caps) == 7
    for c in caps:
        assert c.definition_hash is not None
        assert c.is_stale is False
        assert c.version == 1

@pytest.mark.asyncio
async def test_mcp_discovery_modification_and_stale_detection(db_session):
    user = db_session.query(User).first()
    ws = db_session.query(Workspace).first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Dynamic Server",
        server_url="mock://tools",
        auth_config={
            "mock_tools": [
                {"name": "tool_alpha", "description": "Initial description"},
                {"name": "tool_beta", "description": "Beta description"}
            ],
            "mock_resources": [],
            "mock_prompts": []
        }
    )
    
    discovery = MCPDiscoveryService(db_session)
    
    # 1. First discovery
    res1 = await discovery.discover_capabilities(user.id, ws.id, server.id)
    assert res1["total_tools"] == 2
    assert res1["tools_added"] == 2
    
    # 2. Modify tool_alpha description and remove tool_beta
    server.auth_config = {
        "mock_tools": [
            {"name": "tool_alpha", "description": "Updated modified description"}
        ],
        "mock_resources": [],
        "mock_prompts": []
    }
    db_session.commit()
    
    # 3. Second discovery (detects modification of alpha and marks beta as stale)
    res2 = await discovery.discover_capabilities(user.id, ws.id, server.id)
    assert res2["total_tools"] == 1
    assert res2["tools_changed"] == 1
    assert res2["stale_capabilities"] == 1
    
    alpha = db_session.query(MCPCapability).filter_by(server_id=server.id, name="tool_alpha").first()
    beta = db_session.query(MCPCapability).filter_by(server_id=server.id, name="tool_beta").first()
    
    assert alpha.version == 2
    assert alpha.description == "Updated modified description"
    assert alpha.is_stale is False
    
    assert beta.is_stale is True
    assert beta.stale_at is not None

    # 4. Re-add tool_beta to verify automatic reactivation
    server.auth_config = {
        "mock_tools": [
            {"name": "tool_alpha", "description": "Updated modified description"},
            {"name": "tool_beta", "description": "Beta description"}
        ],
        "mock_resources": [],
        "mock_prompts": []
    }
    db_session.commit()
    
    res3 = await discovery.discover_capabilities(user.id, ws.id, server.id)
    assert res3["reactivated_capabilities"] == 1
    assert res3["unchanged_capabilities"] == 2
    
    db_session.refresh(beta)
    assert beta.is_stale is False
    assert beta.stale_at is None

@pytest.mark.asyncio
async def test_discovery_on_disabled_server_fails(db_session):
    user = db_session.query(User).first()
    ws = db_session.query(Workspace).first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Disabled Server",
        server_url="mock://tools"
    )
    registry.toggle_server(user.id, ws.id, server.id, enabled=False)
    
    discovery = MCPDiscoveryService(db_session)
    with pytest.raises(MCPValidationError) as exc:
        await discovery.discover_capabilities(user.id, ws.id, server.id)
    assert "Cannot discover capabilities on disabled MCP server" in str(exc.value)
