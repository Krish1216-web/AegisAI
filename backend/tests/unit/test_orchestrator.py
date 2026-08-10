import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.orchestrator import (
    OrchestratorAgent, TaskType, Complexity, AgentType, ExecutionPlan, route_orchestrator
)
from app.core.ai.base import ChatResponse, TokenUsage
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    return MagicMock(spec=AIService)

@pytest.mark.asyncio
async def test_orchestrator_mock_mode(mock_ai_service):
    agent = OrchestratorAgent(mock_ai_service)
    
    # Passing 'mock' in prompt triggers mock bypass mode
    state: AgentState = {
        "original_prompt": "Run a mock analysis task",
        "messages": [],
        "agent_outputs": {},
        "token_usage": {},
        "metadata": {}
    }
    context = ExecutionContext(
        request_id="req-11", user_id="u-22", workspace_id="w-33", conversation_id="c-44",
        model="gpt-4o", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.agent_name == "OrchestratorAgent"
    assert result.status == "success"
    
    # Load and verify mock plan contents
    plan_data = json.loads(result.output)
    plan = ExecutionPlan(**plan_data)
    assert plan.task_type == TaskType.GENERAL_QA
    assert plan.complexity == Complexity.SIMPLE
    assert AgentType.RESPONSE_GENERATOR in plan.required_agents

@pytest.mark.asyncio
async def test_orchestrator_real_execution_flow(mock_ai_service):
    agent = OrchestratorAgent(mock_ai_service)
    
    # Mock LLM return plan JSON
    plan = ExecutionPlan(
        task_type=TaskType.RESEARCH,
        complexity=Complexity.MULTI_STEP,
        goal="Collect blockchain reports and summarize discussions",
        steps=["Search papers", "Resolve previous conversations", "Format report"],
        required_agents=[AgentType.RESEARCH, AgentType.MEMORY, AgentType.RESPONSE_GENERATOR],
        requires_memory=True,
        requires_research=True,
        confidence=0.92
    )
    
    mock_ai_service.generate_chat = AsyncMock(return_value=ChatResponse(
        content=plan.model_dump_json(),
        model="gpt-4o-mini",
        provider="openai",
        usage=TokenUsage(prompt_tokens=50, completion_tokens=80, total_tokens=130, estimated_cost=0.0002),
        latency_ms=450
    ))
    
    state: AgentState = {
        "original_prompt": "Research blockchain trends and cross-reference my notes",
        "messages": [],
        "agent_outputs": {},
        "token_usage": {},
        "metadata": {}
    }
    context = ExecutionContext(
        request_id="req-11", user_id="u-22", workspace_id="w-33", conversation_id="c-44",
        model="gpt-4o-mini", provider="openai"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = ExecutionPlan.model_validate_json(result.output)
    assert parsed.task_type == TaskType.RESEARCH
    assert parsed.requires_memory is True
    assert parsed.requires_research is True
    assert AgentType.CRITIC not in parsed.required_agents

def test_route_orchestrator_clarification():
    # If requires_clarification is true, route_orchestrator must return 'END'
    plan = ExecutionPlan(
        task_type=TaskType.UNKNOWN,
        complexity=Complexity.SIMPLE,
        goal="Ambiguous request",
        steps=[],
        required_agents=[],
        requires_clarification=True,
        clarification_question="Could you specify the target dates?",
        confidence=0.5
    )
    state: AgentState = {
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": plan.model_dump_json()
            }
        }
    }
    route = route_orchestrator(state)
    assert route == "END"

def test_route_orchestrator_default_end():
    # Verify default fallback route to END
    state: AgentState = {"agent_outputs": {}}
    route = route_orchestrator(state)
    assert route == "END"
