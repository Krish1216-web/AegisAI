import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_registry import MCPRegistryService
from app.core.mcp.base import MCPValidationError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    # Create Seed User & Workspace
    org = Organization(id=uuid.uuid4(), name="Test Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    user1 = User(id=uuid.uuid4(), email="user1@example.com", username="user1", password_hash="pw", role_id=role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="user2@example.com", username="user2", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace 1")
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace 2")
    
    session.add_all([user1, user2, ws1, ws2])
    session.commit()
    
    yield session
    session.close()

def test_mcp_server_registration_and_get(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="GitHub Integration",
        server_url="http://localhost:8000/sse",
        transport=MCPTransport.SSE,
        description="GitHub MCP Server",
        meta_data={"category": "vcs"}
    )
    
    assert server.id is not None
    assert server.name == "GitHub Integration"
    assert server.status == MCPServerStatus.INACTIVE
    assert server.enabled is True
    assert server.protocol_version == "2024-11-05"
    
    # Get server
    fetched = registry.get_server(user.id, ws.id, server.id)
    assert fetched is not None
    assert fetched.name == "GitHub Integration"

def test_duplicate_server_name_rejection(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    
    registry = MCPRegistryService(db_session)
    registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Postgres MCP",
        server_url="http://localhost:8000/sse"
    )
    
    # Duplicate name should raise validation error
    with pytest.raises(MCPValidationError) as exc:
        registry.register_server(
            user_id=user.id,
            workspace_id=ws.id,
            name="Postgres MCP",
            server_url="http://localhost:8001/sse"
        )
    assert "already registered" in str(exc.value)

def test_duplicate_server_url_rejection(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    
    registry = MCPRegistryService(db_session)
    registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Server A",
        server_url="http://localhost:8000/sse"
    )
    
    # Duplicate URL should raise validation error
    with pytest.raises(MCPValidationError) as exc:
        registry.register_server(
            user_id=user.id,
            workspace_id=ws.id,
            name="Server B",
            server_url="http://localhost:8000/sse"
        )
    assert "already registered in this workspace" in str(exc.value)

def test_server_update_and_toggle(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Old Name",
        server_url="http://localhost:8000/sse"
    )
    
    updated = registry.update_server(
        user_id=user.id,
        workspace_id=ws.id,
        server_id=server.id,
        name="New Name",
        description="Updated description"
    )
    assert updated.name == "New Name"
    assert updated.description == "Updated description"
    
    # Toggle disable
    disabled = registry.toggle_server(user.id, ws.id, server.id, enabled=False)
    assert disabled.enabled is False
    assert disabled.status == MCPServerStatus.DISABLED

def test_server_deletion(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="To Delete",
        server_url="http://localhost:8000/sse"
    )
    
    deleted = registry.delete_server(user.id, ws.id, server.id)
    assert deleted is True
    
    # Verify non-existence
    assert registry.get_server(user.id, ws.id, server.id) is None

@pytest.mark.asyncio
async def test_server_health_check_probe(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user.id,
        workspace_id=ws.id,
        name="Health Ping Server",
        server_url="mock://test-health",
        transport=MCPTransport.SSE
    )
    
    health_res = await registry.check_server_health(user.id, ws.id, server.id)
    assert health_res["is_healthy"] is True
    assert health_res["latency_ms"] is not None
    assert health_res["status"] == "active"
    
    # Verify DB update
    db_session.refresh(server)
    assert server.status == MCPServerStatus.ACTIVE
    assert server.last_health_check_at is not None

def test_catalog_query_and_capability_isolation(db_session):
    user1 = db_session.query(User).filter_by(email="user1@example.com").first()
    user2 = db_session.query(User).filter_by(email="user2@example.com").first()
    ws1 = db_session.query(Workspace).filter_by(name="Workspace 1").first()
    ws2 = db_session.query(Workspace).filter_by(name="Workspace 2").first()
    
    registry = MCPRegistryService(db_session)
    server = registry.register_server(
        user_id=user1.id,
        workspace_id=ws1.id,
        name="Catalog Server",
        server_url="http://localhost:8000/sse"
    )
    
    # Add active and stale capabilities
    cap_active = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="query_analytics",
        description="Query workspace analytics",
        is_stale=False,
        enabled=True
    )
    cap_stale = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="old_tool",
        description="Deprecated tool",
        is_stale=True,
        enabled=True
    )
    db_session.add_all([cap_active, cap_stale])
    db_session.commit()
    
    # List active only
    caps_active, count_active = registry.list_capabilities(user1.id, ws1.id, server.id, include_stale=False)
    assert count_active == 1
    assert caps_active[0].name == "query_analytics"
    
    # List with search term
    caps_searched, count_searched = registry.list_capabilities(user1.id, ws1.id, server.id, search="analytics")
    assert count_searched == 1
    assert caps_searched[0].name == "query_analytics"
    
    # Get capability by ID
    fetched_cap = registry.get_capability(user1.id, ws1.id, cap_active.id)
    assert fetched_cap is not None
    assert fetched_cap.name == "query_analytics"
    
    # Cross-tenant access denied
    assert registry.get_capability(user2.id, ws2.id, cap_active.id) is None
