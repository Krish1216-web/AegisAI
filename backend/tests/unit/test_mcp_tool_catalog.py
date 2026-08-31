import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_tool_catalog import MCPToolCatalogService
from app.core.mcp.policy import ToolRiskLevel

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
    
    user1 = User(id=uuid.uuid4(), email="user1@example.com", username="user1", password_hash="pw", role_id=role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="user2@example.com", username="user2", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace 1")
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace 2")
    
    session.add_all([user1, user2, ws1, ws2])
    session.commit()
    
    yield session
    session.close()

def test_tool_catalog_listing_and_filtering(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()

    server1 = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="GitHub Integration",
        server_url="http://localhost:8000/sse",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    server2 = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Postgres DB",
        server_url="http://localhost:8001/sse",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add_all([server1, server2])
    db_session.commit()

    tool1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="search_github_issues",
        description="Search repository issues",
        enabled=True,
        is_stale=False
    )
    tool2 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server2.id,
        capability_type=MCPCapabilityType.TOOL,
        name="query_sql_database",
        description="Run query against database",
        enabled=True,
        is_stale=False
    )
    db_session.add_all([tool1, tool2])
    db_session.commit()

    catalog = MCPToolCatalogService(db_session)

    # 1. List all tools
    tools, total = catalog.list_tools(user.id, ws.id)
    assert total == 2
    assert len(tools) == 2

    # 2. Filter by server
    server1_tools, count1 = catalog.list_tools(user.id, ws.id, server_id=server1.id)
    assert count1 == 1
    assert server1_tools[0]["name"] == "search_github_issues"

    # 3. Get single tool
    fetched = catalog.get_tool(user.id, ws.id, tool1.id)
    assert fetched is not None
    assert fetched["name"] == "search_github_issues"
    assert fetched["server_name"] == "GitHub Integration"
    assert fetched["available_for_execution"] is True

def test_deterministic_ranked_tool_search(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Main Server",
        server_url="http://localhost:8000/sse",
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    # Create 3 tools with varying relevance to "calculator"
    t_exact = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculator",
        description="Standard arithmetic tool",
        enabled=True,
        is_stale=False
    )
    t_prefix = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculator_advanced",
        description="Advanced scientific formulas",
        enabled=True,
        is_stale=False
    )
    t_desc = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="math_evaluator",
        description="A handy calculator helper for math",
        enabled=True,
        is_stale=False
    )
    db_session.add_all([t_exact, t_prefix, t_desc])
    db_session.commit()

    catalog = MCPToolCatalogService(db_session)
    results = catalog.search_tools(user.id, ws.id, query="calculator")

    assert len(results) == 3
    # Ranking hierarchy: exact match first, prefix second, description match third
    assert results[0]["name"] == "calculator"
    assert results[1]["name"] == "calculator_advanced"
    assert results[2]["name"] == "math_evaluator"

def test_tool_enable_disable_and_availability(db_session):
    user = db_session.query(User).filter_by(email="user1@example.com").first()
    ws = db_session.query(Workspace).filter_by(name="Workspace 1").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Toggle Server",
        server_url="http://localhost:8000/sse",
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="doc_summarizer",
        description="Summarize documents",
        enabled=True,
        is_stale=False
    )
    db_session.add(tool)
    db_session.commit()

    catalog = MCPToolCatalogService(db_session)
    
    # Initially available
    t1 = catalog.get_tool(user.id, ws.id, tool.id)
    assert t1["available_for_execution"] is True

    # Disable tool
    t_disabled = catalog.toggle_tool(user.id, ws.id, tool.id, enabled=False)
    assert t_disabled["enabled"] is False
    assert t_disabled["available_for_execution"] is False

    # When server is disabled, tool is unavailable even if tool.enabled is True
    catalog.toggle_tool(user.id, ws.id, tool.id, enabled=True)
    server.enabled = False
    db_session.commit()

    t_srv_off = catalog.get_tool(user.id, ws.id, tool.id)
    assert t_srv_off["available_for_execution"] is False
