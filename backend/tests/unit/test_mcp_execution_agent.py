import pytest
import uuid
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.core.agent.executor import ToolExecutorAgent
from app.core.agent.tools import ToolRegistry, MockCalculatorTool, MockWeatherTool
from app.core.agent.base import ExecutionContext
from app.core.agent.state import AgentState

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Agent Exec Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    user1 = User(id=uuid.uuid4(), email="agent_u1@test.com", username="agent_u1", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Agent")
    session.add_all([user1, ws1])
    session.commit()
    
    yield session
    session.close()

@pytest.mark.asyncio
async def test_tool_executor_agent_local_and_mcp_flows(db_session):
    user = db_session.query(User).filter_by(email="agent_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Agent").first()

    # Seed MCP Server & Capability
    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Mock MCP Server",
        server_url="mock://agent-test",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    mcp_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        description="Addition helper",
        input_schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        enabled=True,
        is_stale=False
    )
    db_session.add(mcp_tool)
    db_session.commit()

    # Setup Registry with Local Tools
    registry = ToolRegistry()
    registry.register(MockCalculatorTool())
    registry.register(MockWeatherTool())

    agent = ToolExecutorAgent(registry)
    context = ExecutionContext(
        request_id=str(uuid.uuid4()),
        user_id=str(user.id),
        workspace_id=str(ws.id),
        conversation_id=str(uuid.uuid4()),
        model="mock-gpt",
        provider="mock",
        configuration={"db": db_session}
    )

    # 1. Test Local Calculator Execution (Backward compatibility)
    state_local: AgentState = {
        "original_prompt": "calculate 250 * 12",
        "agent_outputs": {
            "PlannerAgent": {
                "output": json.dumps({
                    "steps": [{"step_id": 1, "agent_type": "TOOL_EXECUTOR", "action": "calculator"}]
                })
            }
        },
        "tool_results": []
    }
    res_local = await agent.execute(state_local, context)
    assert res_local.status == "success"
    out_local = json.loads(res_local.output)
    assert out_local["output"]["result"] == 3000

    # 2. Test MCP Tool Execution via Agent
    state_mcp: AgentState = {
        "original_prompt": "use mcp calculator to add numbers",
        "agent_outputs": {
            "PlannerAgent": {
                "output": json.dumps({
                    "steps": [{
                        "step_id": 1,
                        "agent_type": "TOOL_EXECUTOR",
                        "tool_source": "MCP",
                        "action": "mcp:calculate_sum",
                        "tool_id": str(mcp_tool.id)
                    }]
                })
            }
        },
        "tool_results": []
    }
    context_mcp = ExecutionContext(
        request_id=str(uuid.uuid4()),
        user_id=str(user.id),
        workspace_id=str(ws.id),
        conversation_id=str(uuid.uuid4()),
        model="mock-gpt",
        provider="mock",
        configuration={"db": db_session}
    )
    res_mcp = await agent.execute(state_mcp, context_mcp)
    assert res_mcp.status == "success"
    out_mcp = json.loads(res_mcp.output)
    assert out_mcp["metadata"]["source"] == "MCP"
