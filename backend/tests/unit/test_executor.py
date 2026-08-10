import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.orchestrator import ExecutionPlan, TaskType, Complexity, AgentType
from app.core.agent.planner import DetailedExecutionPlan, PlanStep
from app.core.agent.tools import (
    ToolRegistry, MockCalculatorTool, MockSearchTool, MockDocumentReaderTool, MockWeatherTool,
    ToolDefinition, ToolCategory, RiskLevel, ToolExecutionStatus, generate_confirmation_token
)
from app.core.agent.executor import ToolExecutorAgent
from app.core.agent.exceptions import (
    ToolNotFound, ToolDisabled, ToolPermissionDenied, ToolArgumentValidationError,
    ToolConfirmationInvalid, ToolAlreadyExecuted, ToolRegistryError
)

@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(MockCalculatorTool())
    reg.register(MockSearchTool())
    reg.register(MockDocumentReaderTool())
    reg.register(MockWeatherTool())
    return reg

def test_registry_registration_duplicate_check():
    reg = ToolRegistry()
    tool = MockCalculatorTool()
    reg.register(tool)
    with pytest.raises(ToolRegistryError):
        reg.register(tool) # Duplicate ID raises error

def test_calculator_operations():
    tool = MockCalculatorTool()
    # Programmatic execution test
    # Multiply
    assert tool.definition().tool_id == "calculator"
    # Execute multiplication mock runner directly
    ctx = {"user_id": "u", "workspace_id": "ws"}
    
    import asyncio
    async def run():
        res = await tool.execute({"operation": "multiply", "a": 5, "b": 6}, ctx)
        assert res["result"] == 30
    asyncio.run(run())

@pytest.mark.asyncio
async def test_executor_calculator_run(registry):
    agent = ToolExecutorAgent(registry)
    state: AgentState = {
        "original_prompt": "Calculate 250 * 12",
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "metadata": {}
    }
    context = ExecutionContext(
        request_id="req-100", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = json.loads(result.output)
    assert parsed["status"] == "SUCCESS"
    assert parsed["output"]["result"] == 3000
    
    # State check: tool_results must be updated
    assert len(state["tool_results"]) == 1
    assert state["tool_results"][0]["tool_id"] == "calculator"

@pytest.mark.asyncio
async def test_executor_idempotency_check(registry):
    agent = ToolExecutorAgent(registry)
    state: AgentState = {
        "original_prompt": "Calculate 250 * 12",
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "metadata": {}
    }
    context = ExecutionContext(
        request_id="req-100", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    # First execution succeeds
    await agent.execute(state, context)
    
    # Second execution with same request_id/idempotency key raises error
    with pytest.raises(ToolAlreadyExecuted):
        await agent.execute(state, context)

@pytest.mark.asyncio
async def test_executor_confirmation_workflow(registry):
    agent = ToolExecutorAgent(registry)
    
    # MockWeatherTool requires human confirmation
    state: AgentState = {
        "original_prompt": "Get weather update",
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "metadata": {} # No confirmation token provided initially
    }
    context = ExecutionContext(
        request_id="req-200", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "requires_confirmation"
    
    parsed = json.loads(result.output)
    assert parsed["status"] == "REQUIRES_CONFIRMATION"
    token = parsed["metadata"]["confirmation_token"]
    assert token is not None

    # Supply correct confirmation token
    state["metadata"]["confirmation_token"] = token
    result_confirmed = await agent.execute(state, context)
    assert result_confirmed.status == "success"
    
    parsed_confirmed = json.loads(result_confirmed.output)
    assert parsed_confirmed["status"] == "SUCCESS"

    # Supply incorrect confirmation token
    state["metadata"]["confirmation_token"] = "invalid_token_xyz"
    # We clear idempotency execution first to trigger path
    agent.executed_keys.clear()
    
    with pytest.raises(ToolConfirmationInvalid):
        await agent.execute(state, context)

@pytest.mark.asyncio
async def test_orchestrator_planner_executor_integration(registry):
    orch_plan = ExecutionPlan(
        task_type=TaskType.MIXED_TASK,
        complexity=Complexity.SIMPLE,
        goal="Calculate",
        steps=["calculator"],
        required_agents=[AgentType.TOOL_EXECUTOR],
        confidence=0.9
    )
    
    planner_plan = DetailedExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1", title="Calculate product", description="Calculate multiplication",
                agent_type=AgentType.TOOL_EXECUTOR, action="calculator", expected_output="product result"
            )
        ]
    )
    
    agent = ToolExecutorAgent(registry)
    
    state: AgentState = {
        "original_prompt": "Calculate product",
        "messages": [],
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": orch_plan.model_dump_json()
            },
            "PlannerAgent": {
                "output": planner_plan.model_dump_json()
            }
        },
        "tool_results": [],
        "metadata": {}
    }
    
    context = ExecutionContext(
        request_id="req-300", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = json.loads(result.output)
    assert parsed["status"] == "SUCCESS"
    assert parsed["output"]["result"] == 3000
