import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_tool_executor import MCPToolExecutionService
from app.core.mcp.base import MCPValidationError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Test Exec Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    user1 = User(id=uuid.uuid4(), email="u1@test.com", username="u1", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Exec")
    session.add_all([user1, ws1])
    session.commit()
    
    yield session
    session.close()

@pytest.mark.asyncio
async def test_successful_safe_tool_execution(db_session):
    user = db_session.query(User).filter_by(email="u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Exec").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Math Mock Server",
        server_url="mock://math",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        description="Adds two numbers together",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        },
        enabled=True,
        is_stale=False
    )
    db_session.add(tool)
    db_session.commit()

    executor = MCPToolExecutionService(db_session)
    res = await executor.execute_tool(
        user_id=user.id,
        workspace_id=ws.id,
        tool_id=tool.id,
        arguments={"a": 15, "b": 25}
    )

    assert res.status == "SUCCESS"
    assert res.result["sum"] == 40
    assert res.duration_ms >= 0

@pytest.mark.asyncio
async def test_execution_validation_errors(db_session):
    user = db_session.query(User).filter_by(email="u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Exec").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Mock Server",
        server_url="mock://test",
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        },
        enabled=True,
        is_stale=False
    )
    db_session.add(tool)
    db_session.commit()

    executor = MCPToolExecutionService(db_session)

    # 1. Missing required field
    with pytest.raises(MCPValidationError) as exc1:
        await executor.execute_tool(user.id, ws.id, tool.id, arguments={"a": 10})
    assert "Missing required parameter 'b'" in str(exc1.value)

    # 2. Type mismatch
    with pytest.raises(MCPValidationError) as exc2:
        await executor.execute_tool(user.id, ws.id, tool.id, arguments={"a": "not_a_number", "b": 5})
    assert "must be a number" in str(exc2.value)

    # 3. Tool disabled rejection
    tool.enabled = False
    db_session.commit()
    with pytest.raises(MCPValidationError) as exc3:
        await executor.execute_tool(user.id, ws.id, tool.id, arguments={"a": 5, "b": 5})
    assert "Tool 'calculate_sum' is disabled" in str(exc3.value)

    # 4. Server disabled rejection
    tool.enabled = True
    server.enabled = False
    db_session.commit()
    with pytest.raises(MCPValidationError) as exc4:
        await executor.execute_tool(user.id, ws.id, tool.id, arguments={"a": 5, "b": 5})
    assert "MCP server 'Mock Server' is disabled" in str(exc4.value)

    # 5. Stale tool rejection
    server.enabled = True
    tool.is_stale = True
    db_session.commit()
    with pytest.raises(MCPValidationError) as exc5:
        await executor.execute_tool(user.id, ws.id, tool.id, arguments={"a": 5, "b": 5})
    assert "is stale" in str(exc5.value)
