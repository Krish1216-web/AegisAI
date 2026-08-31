import pytest
import uuid
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.core.agent.tools import ToolRegistry, MockCalculatorTool
from app.core.agent.executor import ToolExecutorAgent
from app.core.agent.critic import CriticAgent, CriticDecision
from app.core.agent.response import ResponseGeneratorAgent
from app.core.agent.base import ExecutionContext
from app.core.agent.state import AgentState
from app.core.agent.exceptions import ToolConfirmationRequired

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Agent Integration Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()

    u1 = User(id=uuid.uuid4(), email="agent_int1@test.com", username="ai1", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Agent Int")
    session.add_all([u1, ws1])
    session.commit()

    mem = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws1.id, user_id=u1.id, role="member")
    session.add(mem)
    session.commit()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=u1.id,
        workspace_id=ws1.id,
        name="Mock MCP Server",
        server_url="mock://agent-integration",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    session.add(server)
    session.commit()

    # 1. Safe Tool
    safe_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        description="Adds numbers safely",
        input_schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        enabled=True,
        is_stale=False
    )
    # 2. Restricted Tool
    restricted_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="execute_shell_command",
        description="Executes bash shell script",
        input_schema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        enabled=True,
        is_stale=False
    )
    # 3. Resource
    resource = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="project_architecture_spec",
        description="Architecture specification doc",
        input_schema={"uri": "workspace://docs/arch.md", "mime_type": "text/markdown"},
        enabled=True,
        is_stale=False
    )
    # 4. Prompt
    prompt_cap = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.PROMPT,
        name="sprint_planning_template",
        description="Template for agile sprint planning",
        input_schema={"arguments": [{"name": "sprint_goal", "required": False}]},
        enabled=True,
        is_stale=False
    )
    session.add_all([safe_tool, restricted_tool, resource, prompt_cap])
    session.commit()

    yield session
    session.close()

@pytest.fixture
def mock_ai_service():
    class MockAIService:
        pass
    return MockAIService()

@pytest.mark.asyncio
async def test_tool_executor_safe_mcp_tool_execution(db_session):
    user = db_session.query(User).filter_by(email="agent_int1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Agent Int").first()
    safe_tool = db_session.query(MCPCapability).filter_by(name="calculate_sum").first()

    registry = ToolRegistry()
    executor = ToolExecutorAgent(registry)

    context = ExecutionContext(
        request_id=str(uuid.uuid4()),
        user_id=str(user.id),
        workspace_id=str(ws.id),
        conversation_id=str(uuid.uuid4()),
        model="mock-gpt",
        provider="mock",
        configuration={"db": db_session}
    )

    state: AgentState = {
        "original_prompt": "use mcp calculator",
        "agent_outputs": {
            "PlannerAgent": {
                "output": json.dumps({
                    "steps": [{
                        "step_id": "step_1",
                        "agent_type": "TOOL_EXECUTOR",
                        "tool_source": "MCP",
                        "action": "mcp:calculate_sum",
                        "tool_id": str(safe_tool.id)
                    }]
                })
            }
        },
        "tool_results": []
    }

    result = await executor.execute(state, context)
    assert result.status == "success"
    tool_output = json.loads(result.output)
    assert tool_output["status"] == "SUCCESS"
    assert tool_output["output"]["sum"] == 262

@pytest.mark.asyncio
async def test_tool_executor_restricted_mcp_tool_pauses_for_confirmation(db_session):
    user = db_session.query(User).filter_by(email="agent_int1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Agent Int").first()
    restr_tool = db_session.query(MCPCapability).filter_by(name="execute_shell_command").first()

    registry = ToolRegistry()
    executor = ToolExecutorAgent(registry)

    context = ExecutionContext(
        request_id=str(uuid.uuid4()),
        user_id=str(user.id),
        workspace_id=str(ws.id),
        conversation_id=str(uuid.uuid4()),
        model="mock-gpt",
        provider="mock",
        configuration={"db": db_session}
    )

    state: AgentState = {
        "original_prompt": "run shell command",
        "agent_outputs": {
            "PlannerAgent": {
                "output": json.dumps({
                    "steps": [{
                        "step_id": "step_1",
                        "agent_type": "TOOL_EXECUTOR",
                        "tool_source": "MCP",
                        "action": "mcp:execute_shell_command",
                        "tool_id": str(restr_tool.id)
                    }]
                })
            }
        },
        "tool_results": []
    }

    with pytest.raises(ToolConfirmationRequired):
        await executor.execute(state, context)

    assert "mcp_pending_confirmation" in state
    assert state["mcp_pending_confirmation"]["tool_id"] == str(restr_tool.id)

@pytest.mark.asyncio
async def test_tool_executor_mcp_resource_read_flow(db_session):
    user = db_session.query(User).filter_by(email="agent_int1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Agent Int").first()
    resource = db_session.query(MCPCapability).filter_by(name="project_architecture_spec").first()

    registry = ToolRegistry()
    executor = ToolExecutorAgent(registry)

    context = ExecutionContext(
        request_id=str(uuid.uuid4()),
        user_id=str(user.id),
        workspace_id=str(ws.id),
        conversation_id=str(uuid.uuid4()),
        model="mock-gpt",
        provider="mock",
        configuration={"db": db_session}
    )

    state: AgentState = {
        "original_prompt": "read project architecture spec",
        "agent_outputs": {
            "PlannerAgent": {
                "output": json.dumps({
                    "steps": [{
                        "step_id": "step_1",
                        "agent_type": "TOOL_EXECUTOR",
                        "tool_source": "MCP",
                        "action": "mcp:read_resource",
                        "tool_id": str(resource.id),
                        "capability_type": "RESOURCE"
                    }]
                })
            }
        },
        "tool_results": []
    }

    result = await executor.execute(state, context)
    assert result.status == "success"
    assert "mcp_resource_context" in state
    assert state["mcp_resource_context"] is not None

@pytest.mark.asyncio
async def test_critic_validates_mcp_provenance_and_rejects_fabricated_citations(mock_ai_service):
    critic = CriticAgent(mock_ai_service)
    context = ExecutionContext(
        request_id="crit-1",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )

    # 1. Valid MCP citations succeed
    state_valid: AgentState = {
        "original_prompt": "summarize project spec",
        "mcp_citations": [{
            "source_type": "mcp_resource",
            "server_id": "srv-1",
            "resource_id": "res-1",
            "title": "Architecture Spec"
        }]
    }
    res_valid = await critic.execute(state_valid, context)
    crit_valid = json.loads(res_valid.output)
    assert crit_valid["decision"] == CriticDecision.ACCEPT.value

    # 2. Fabricated MCP citations fail
    state_fab: AgentState = {
        "original_prompt": "summarize project spec",
        "mcp_citations": [{
            "source_type": "mcp_resource",
            "server_id": "fabricated_server",
            "resource_id": "invalid_resource",
            "title": "Fake Spec"
        }]
    }
    res_fab = await critic.execute(state_fab, context)
    crit_fab = json.loads(res_fab.output)
    assert crit_fab["decision"] == CriticDecision.FAIL.value

@pytest.mark.asyncio
async def test_response_generator_source_attribution(mock_ai_service):
    response_gen = ResponseGeneratorAgent(mock_ai_service)
    context = ExecutionContext(
        request_id="resp-1",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )

    state: AgentState = {
        "original_prompt": "compare github issue with document spec",
        "mcp_resource_context": "Architecture spec: Microservices with MCP interface",
        "tool_results": [{
            "tool_id": "mcp:github_issue",
            "status": "SUCCESS",
            "output": {"issue_id": "#101", "title": "Memory leak fix"},
            "metadata": {"source": "MCP", "tool_name": "github_issue"}
        }],
        "mcp_citations": [{
            "source_type": "mcp_resource",
            "resource_id": "res-spec",
            "title": "Project Specification",
            "uri": "workspace://docs/spec.md"
        }],
        "agent_outputs": {
            "CriticAgent": {
                "output": json.dumps({"decision": "ACCEPT", "overall_score": 1.0})
            }
        }
    }

    result = await response_gen.execute(state, context)
    assert result.status == "success"
    resp_data = json.loads(result.output)
    assert "[MCP Tool: github_issue]" in resp_data["content"]
    assert "MCP Resource Evidence" in resp_data["content"]
    assert len(resp_data["citations"]) >= 1
    assert resp_data["citations"][0]["source_type"] == "mcp_resource"
