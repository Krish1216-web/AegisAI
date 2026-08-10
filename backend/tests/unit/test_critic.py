import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.orchestrator import ExecutionPlan, TaskType, Complexity, AgentType
from app.core.agent.planner import DetailedExecutionPlan, PlanStep
from app.core.agent.critic import CriticAgent, CriticResult, CriticIssue, CriticDecision, route_critic
from app.core.ai.base import ChatResponse, TokenUsage
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    return MagicMock(spec=AIService)

def test_critic_result_validation():
    # Verify Pydantic validation handles valid CriticResult structures
    res = CriticResult(
        execution_id="exec-1",
        decision=CriticDecision.ACCEPT,
        overall_score=0.9,
        confidence=0.85,
        summary="Plan executed perfectly",
        issues=[]
    )
    assert res.decision == CriticDecision.ACCEPT
    assert res.overall_score == 0.9

@pytest.mark.asyncio
async def test_critic_retry_limit_protection(mock_ai_service):
    agent = CriticAgent(mock_ai_service)
    
    # State has retry_count = 3 (Max limit reached)
    state: AgentState = {
        "original_prompt": "Run computation mock",
        "retry_count": 3,
        "messages": [],
        "agent_outputs": {},
        "tool_results": []
    }
    context = ExecutionContext(
        request_id="req-1", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "failed"
    
    parsed = json.loads(result.output)
    assert parsed["decision"] == "FAIL"
    assert parsed["issues"][0]["issue_id"] == "loop_limit"

@pytest.mark.asyncio
async def test_critic_failed_tool_routing(mock_ai_service):
    agent = CriticAgent(mock_ai_service)
    
    # Tool results contains a FAILED execution status
    state: AgentState = {
        "original_prompt": "Run mock calculation",
        "retry_count": 0,
        "messages": [],
        "agent_outputs": {},
        "tool_results": [
            {"execution_id": "req-1", "tool_id": "calculator", "status": "FAILED", "execution_time": 0.05}
        ]
    }
    context = ExecutionContext(
        request_id="req-1", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    parsed = json.loads(result.output)
    assert parsed["decision"] == "TOOL_RETRY"

@pytest.mark.asyncio
async def test_critic_security_isolation_violation(mock_ai_service):
    agent = CriticAgent(mock_ai_service)
    
    # User B workspace contains memory context leakage belonging to User A
    state: AgentState = {
        "original_prompt": "Query coding info mock",
        "retry_count": 0,
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "memory_context": "Relevant context: User A prefers Java examples."
    }
    context = ExecutionContext(
        request_id="req-1", user_id="user-B", workspace_id="ws-B", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    parsed = json.loads(result.output)
    assert parsed["decision"] == "FAIL"
    assert parsed["issues"][0]["issue_id"] == "tenant_isolation_violation"

@pytest.mark.asyncio
async def test_orchestrator_planner_research_memory_executor_critic_integration(mock_ai_service):
    # Tests a complete execution pipeline state evaluation
    orch_plan = ExecutionPlan(
        task_type=TaskType.MIXED_TASK, complexity=Complexity.SIMPLE, goal="Calculate results",
        steps=["calculator"], required_agents=[AgentType.TOOL_EXECUTOR], confidence=0.9
    )
    planner_plan = DetailedExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1", title="Calculate product", description="Calculate multiplication",
                agent_type=AgentType.TOOL_EXECUTOR, action="calculator", expected_output="product result"
            )
        ]
    )
    
    agent = CriticAgent(mock_ai_service)
    
    state: AgentState = {
        "original_prompt": "Calculate product mock",
        "retry_count": 0,
        "messages": [],
        "agent_outputs": {
            "OrchestratorAgent": {"output": orch_plan.model_dump_json()},
            "PlannerAgent": {"output": planner_plan.model_dump_json()}
        },
        "tool_results": [
            {"execution_id": "req-1", "tool_id": "calculator", "status": "SUCCESS", "output": {"result": 3000}, "execution_time": 0.05}
        ],
        "research_results": "Mock research results content",
        "memory_context": "User A prefers Java"
    }
    
    context = ExecutionContext(
        request_id="req-1", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = json.loads(result.output)
    assert parsed["decision"] == "ACCEPT"

def test_route_critic_mapping():
    # ACCEPT decision should route toRESPONSE_GENERATOR
    state_accept: AgentState = {
        "agent_outputs": {
            "CriticAgent": {
                "output": json.dumps({"decision": "ACCEPT"})
            }
        }
    }
    assert route_critic(state_accept) == "RESPONSE_GENERATOR"

    # RESEARCH_MORE decision should route to ResearchAgent
    state_research: AgentState = {
        "agent_outputs": {
            "CriticAgent": {
                "output": json.dumps({"decision": "RESEARCH_MORE"})
            }
        }
    }
    assert route_critic(state_research) == "ResearchAgent"
