import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.orchestrator import OrchestratorAgent, ExecutionPlan, TaskType, Complexity, AgentType
from app.core.agent.planner import PlannerAgent, DetailedExecutionPlan, PlanStep
from app.core.agent.exceptions import AgentValidationError
from app.core.ai.base import ChatResponse, TokenUsage
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    return MagicMock(spec=AIService)

def test_circular_dependency_check(mock_ai_service):
    planner = PlannerAgent(mock_ai_service)
    
    # step_1 -> step_2 -> step_1 (Cycle)
    steps = [
        PlanStep(
            step_id="step_1", title="A", description="A", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=["step_2"]
        ),
        PlanStep(
            step_id="step_2", title="B", description="B", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=["step_1"]
        )
    ]
    
    assert planner._detect_circular_dependencies(steps) is True

def test_no_circular_dependency(mock_ai_service):
    planner = PlannerAgent(mock_ai_service)
    
    # step_1 -> step_2
    steps = [
        PlanStep(
            step_id="step_1", title="A", description="A", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=[]
        ),
        PlanStep(
            step_id="step_2", title="B", description="B", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=["step_1"]
        )
    ]
    
    assert planner._detect_circular_dependencies(steps) is False

def test_duplicate_step_ids(mock_ai_service):
    planner = PlannerAgent(mock_ai_service)
    
    steps = [
        PlanStep(
            step_id="step_1", title="A", description="A", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=[]
        ),
        PlanStep(
            step_id="step_1", title="B", description="B", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=[]
        )
    ]
    plan = DetailedExecutionPlan(steps=steps)
    
    with pytest.raises(AgentValidationError):
        planner.validate_plan_schema(plan)

def test_missing_dependency_reference(mock_ai_service):
    planner = PlannerAgent(mock_ai_service)
    
    steps = [
        PlanStep(
            step_id="step_1", title="A", description="A", agent_type=AgentType.RESEARCH,
            action="act", expected_output="out", dependencies=["non_existent_step"]
        )
    ]
    plan = DetailedExecutionPlan(steps=steps)
    
    with pytest.raises(AgentValidationError):
        planner.validate_plan_schema(plan)

@pytest.mark.asyncio
async def test_planner_permission_denied(mock_ai_service):
    planner = PlannerAgent(mock_ai_service)
    
    plan = DetailedExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1", title="Commit code", description="Push to main",
                agent_type=AgentType.TOOL_EXECUTOR, action="github_commit", expected_output="commit hash"
            )
        ]
    )
    
    mock_ai_service.generate_chat = AsyncMock(return_value=ChatResponse(
        content=plan.model_dump_json(),
        model="gpt-4o-mini",
        provider="openai",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        latency_ms=100
    ))
    
    state: AgentState = {
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": "{}"
            }
        }
    }
    
    # Context lacks 'github' permission parameter
    context = ExecutionContext(
        request_id="req-1", user_id="u-1", workspace_id="w-1", conversation_id="c-1",
        permissions=["read_only"], model="gpt-4", provider="openai"
    )
    
    with pytest.raises(AgentValidationError) as exc:
        await planner.execute(state, context)
        
    assert "Permission denied" in str(exc.value)

@pytest.mark.asyncio
async def test_orchestrator_to_planner_integration(mock_ai_service):
    # Tests that the output of the Orchestrator serves as a valid input transition to the Planner
    orch_plan = ExecutionPlan(
        task_type=TaskType.RESEARCH,
        complexity=Complexity.SIMPLE,
        goal="Consolidate research",
        steps=["Search trends"],
        required_agents=[AgentType.RESPONSE_GENERATOR],
        confidence=0.9
    )
    
    planner = PlannerAgent(mock_ai_service)
    
    state: AgentState = {
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": orch_plan.model_dump_json()
            }
        },
        "original_prompt": "mock execution integration query"
    }
    
    context = ExecutionContext(
        request_id="req-1", user_id="u-1", workspace_id="w-1", conversation_id="c-1",
        permissions=["github"], model="gpt-4", provider="mock"
    )
    
    result = await planner.execute(state, context)
    assert result.status == "success"
    
    parsed = DetailedExecutionPlan.model_validate_json(result.output)
    assert len(parsed.steps) == 1
    assert parsed.steps[0].agent_type == AgentType.RESPONSE_GENERATOR
