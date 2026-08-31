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
    assert res["added_capabilities"] == 7
    
    # Check database records
    caps = db_session.query(MCPCapability).filter_by(server_id=server.id).all()
    assert len(caps) == 7
    
    # Verify tools
    tools = [c for c in caps if c.capability_type == MCPCapabilityType.TOOL]
    assert len(tools) == 3
    tool_names = {t.name for t in tools}
    assert "calculate_sum" in tool_names
    assert "query_database" in tool_names

@pytest.mark.asyncio
async def test_mcp_discovery_stale_pruning(db_session):
    user = db_session.query(User).first()
    ws = db_session.query(Workspace).first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Pruning Server",
        server_url="mock://tools",
        auth_config={
            "mock_tools": [
                {"name": "tool_alpha", "description": "Alpha tool"},
                {"name": "tool_beta", "description": "Beta tool"}
            ],
            "mock_resources": [],
            "mock_prompts": []
        }
    )
    
    discovery = MCPDiscoveryService(db_session)
    # First discovery: 2 tools
    res1 = await discovery.discover_capabilities(user.id, ws.id, server.id)
    assert res1["total_tools"] == 2
    
    # Re-configure server with only tool_alpha
    server.auth_config = {
        "mock_tools": [
            {"name": "tool_alpha", "description": "Updated Alpha tool"}
        ],
        "mock_resources": [],
        "mock_prompts": []
    }
    db_session.commit()
    
    # Second discovery with pruning
    res2 = await discovery.discover_capabilities(user.id, ws.id, server.id, prune_stale=True)
    assert res2["total_tools"] == 1
    assert res2["pruned_capabilities"] == 1
    assert res2["updated_capabilities"] == 1
    
    caps = db_session.query(MCPCapability).filter_by(server_id=server.id).all()
    assert len(caps) == 1
    assert caps[0].name == "tool_alpha"
    assert caps[0].description == "Updated Alpha tool"

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
