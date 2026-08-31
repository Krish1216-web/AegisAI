import pytest
import json
from app.core.agent.planner import PlannerAgent, PlanStep, DetailedExecutionPlan
from app.core.agent.orchestrator import TaskType, AgentType, ExecutionPlan, Complexity
from app.core.agent.base import ExecutionContext
from app.core.agent.state import AgentState

@pytest.fixture
def mock_ai_service():
    class MockAIService:
        pass
    return MockAIService()

@pytest.fixture
def planner(mock_ai_service):
    return PlannerAgent(mock_ai_service)

@pytest.mark.asyncio
async def test_mcp_tool_step_generation(planner):
    context = ExecutionContext(
        request_id="plan-1",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    orch_plan = ExecutionPlan(
        task_type=TaskType.MCP_TOOL,
        complexity=Complexity.SIMPLE,
        goal="Create GitHub issue",
        steps=["Execute MCP Tool"],
        required_agents=[AgentType.TOOL_EXECUTOR],
        requires_mcp=True,
        mcp_operation="tool",
        confidence=0.95
    )
    state: AgentState = {
        "original_prompt": "Create an issue in GitHub for this bug",
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": orch_plan.model_dump_json()
            }
        }
    }
    result = await planner.execute(state, context)
    assert result.status == "success"
    det_plan = DetailedExecutionPlan.model_validate_json(result.output)
    assert len(det_plan.steps) >= 1
    mcp_steps = [s for s in det_plan.steps if s.tool_source == "MCP"]
    assert len(mcp_steps) == 1
    assert mcp_steps[0].capability_type == "TOOL"
    assert mcp_steps[0].action == "mcp:execute_tool"

@pytest.mark.asyncio
async def test_mcp_resource_step_generation(planner):
    context = ExecutionContext(
        request_id="plan-2",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    orch_plan = ExecutionPlan(
        task_type=TaskType.MCP_RESOURCE,
        complexity=Complexity.SIMPLE,
        goal="Read connected project documentation",
        steps=["Read Resource"],
        required_agents=[AgentType.TOOL_EXECUTOR],
        requires_mcp=True,
        mcp_operation="resource",
        confidence=0.95
    )
    state: AgentState = {
        "original_prompt": "Read my connected project documentation",
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": orch_plan.model_dump_json()
            }
        }
    }
    result = await planner.execute(state, context)
    assert result.status == "success"
    det_plan = DetailedExecutionPlan.model_validate_json(result.output)
    mcp_steps = [s for s in det_plan.steps if s.tool_source == "MCP"]
    assert len(mcp_steps) == 1
    assert mcp_steps[0].capability_type == "RESOURCE"
    assert mcp_steps[0].can_run_parallel is True

@pytest.mark.asyncio
async def test_mcp_prompt_step_generation(planner):
    context = ExecutionContext(
        request_id="plan-3",
        user_id="u1",
        workspace_id="ws1",
        conversation_id="conv1",
        model="mock-gpt",
        provider="mock"
    )
    orch_plan = ExecutionPlan(
        task_type=TaskType.MCP_PROMPT,
        complexity=Complexity.SIMPLE,
        goal="Render connected prompt template",
        steps=["Render Prompt"],
        required_agents=[AgentType.TOOL_EXECUTOR],
        requires_mcp=True,
        mcp_operation="prompt",
        confidence=0.95
    )
    state: AgentState = {
        "original_prompt": "Use the connected project planning template",
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": orch_plan.model_dump_json()
            }
        }
    }
    result = await planner.execute(state, context)
    assert result.status == "success"
    det_plan = DetailedExecutionPlan.model_validate_json(result.output)
    mcp_steps = [s for s in det_plan.steps if s.tool_source == "MCP"]
    assert len(mcp_steps) == 1
    assert mcp_steps[0].capability_type == "PROMPT"
