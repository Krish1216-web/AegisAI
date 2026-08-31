import pytest
import json
from app.core.agent.orchestrator import OrchestratorAgent, TaskType, AgentType, ExecutionPlan
from app.core.agent.base import ExecutionContext
from app.core.agent.state import AgentState
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    class MockAIService:
        pass
    return MockAIService()

@pytest.fixture
def orchestrator(mock_ai_service):
    return OrchestratorAgent(mock_ai_service)

@pytest.mark.asyncio
async def test_mcp_tool_query_classification(orchestrator):
    context = ExecutionContext(
        request_id="req-1",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    state: AgentState = {"original_prompt": "Create an issue in GitHub for this bug"}
    result = await orchestrator.execute(state, context)
    assert result.status == "success"
    plan = ExecutionPlan.model_validate_json(result.output)
    assert plan.task_type == TaskType.MCP_TOOL
    assert plan.requires_mcp is True
    assert plan.mcp_operation == "tool"
    assert AgentType.TOOL_EXECUTOR in plan.required_agents

@pytest.mark.asyncio
async def test_mcp_resource_query_classification(orchestrator):
    context = ExecutionContext(
        request_id="req-2",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    state: AgentState = {"original_prompt": "Read my connected project documentation and summarize it"}
    result = await orchestrator.execute(state, context)
    assert result.status == "success"
    plan = ExecutionPlan.model_validate_json(result.output)
    assert plan.task_type == TaskType.MCP_RESOURCE
    assert plan.requires_mcp is True
    assert plan.mcp_operation == "resource"

@pytest.mark.asyncio
async def test_mcp_prompt_query_classification(orchestrator):
    context = ExecutionContext(
        request_id="req-3",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    state: AgentState = {"original_prompt": "Use the connected project planning template for our sprint"}
    result = await orchestrator.execute(state, context)
    assert result.status == "success"
    plan = ExecutionPlan.model_validate_json(result.output)
    assert plan.task_type == TaskType.MCP_PROMPT
    assert plan.requires_mcp is True
    assert plan.mcp_operation == "prompt"

@pytest.mark.asyncio
async def test_non_mcp_query_does_not_route_to_mcp(orchestrator):
    context = ExecutionContext(
        request_id="req-4",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    # Local calculator query
    state_calc: AgentState = {"original_prompt": "Calculate 250 multiplied by 12"}
    res_calc = await orchestrator.execute(state_calc, context)
    plan_calc = ExecutionPlan.model_validate_json(res_calc.output)
    assert plan_calc.requires_mcp is False
    assert plan_calc.task_type != TaskType.MCP_TOOL

    # Web research query
    state_res: AgentState = {"original_prompt": "Search the internet for competitors in AI space"}
    res_res = await orchestrator.execute(state_res, context)
    plan_res = ExecutionPlan.model_validate_json(res_res.output)
    assert plan_res.requires_mcp is False
    assert plan_res.task_type == TaskType.RESEARCH

@pytest.mark.asyncio
async def test_mcp_hybrid_query_classification(orchestrator):
    context = ExecutionContext(
        request_id="req-5",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    state: AgentState = {"original_prompt": "Find the latest GitHub issue and compare it with our uploaded architecture document"}
    result = await orchestrator.execute(state, context)
    assert result.status == "success"
    plan = ExecutionPlan.model_validate_json(result.output)
    assert plan.task_type == TaskType.MCP_HYBRID
    assert plan.requires_mcp is True
    assert plan.requires_rag is True
