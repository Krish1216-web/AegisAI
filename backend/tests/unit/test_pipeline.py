import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.checkpoint import InMemoryCheckpointer
from app.core.agent.pipeline import AegisAIPipeline
from app.core.agent.exceptions import (
    GraphExecutionError, ToolPermissionDenied, MemoryPermissionError, ToolConfirmationInvalid
)
from app.core.agent.response import ResponseGenerationResult, ResponseStatus
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    return MagicMock(spec=AIService)

@pytest.mark.asyncio
async def test_pipeline_basic_calculation_e2e(mock_ai_service):
    # E2E test verifying math pipeline: Orchestrator -> Planner -> Memory -> Executor -> Critic -> Response
    pipeline = AegisAIPipeline(mock_ai_service)
    
    state = pipeline.build_initial_state(
        user_id="user-123",
        workspace_id="ws-abc",
        execution_id="exec-e2e-1",
        original_prompt="Calculate 250 * 12 and explain the result using my relevant project context.",
        provider="mock"
    )
    
    final_state = await pipeline.execute(state)
    assert final_state["execution_status"] == ExecutionStatus.COMPLETED
    assert final_state["final_response"] is not None
    assert "3,000" in final_state["final_response"]
    
    # Assert security: no credentials or stack traces in final response
    assert "sk-" not in final_state["final_response"]
    assert "Traceback" not in final_state["final_response"]

@pytest.mark.asyncio
async def test_pipeline_research_e2e(mock_ai_service):
    # E2E research pipeline: Orchestrator -> Planner -> Research -> Critic -> Response
    pipeline = AegisAIPipeline(mock_ai_service)
    
    state = pipeline.build_initial_state(
        user_id="user-123",
        workspace_id="ws-abc",
        execution_id="exec-e2e-2",
        original_prompt="Research blockchain trends mock",
        provider="mock"
    )
    
    final_state = await pipeline.execute(state)
    assert final_state["execution_status"] == ExecutionStatus.COMPLETED
    
    resp_obj = json.loads(final_state["agent_outputs"]["ResponseGeneratorAgent"]["output"])
    assert len(resp_obj["citations"]) > 0
    assert resp_obj["citations"][0]["source_id"] is not None

@pytest.mark.asyncio
async def test_pipeline_tool_failure_limit(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    # Register failing calculator tool
    mock_calc = MagicMock()
    mock_calc.definition.return_value.tool_id = "calculator"
    mock_calc.definition.return_value.enabled = True
    mock_calc.definition.return_value.requires_confirmation = False
    mock_calc.definition.return_value.required_permissions = []
    # Fail during execution
    mock_calc.execute = AsyncMock(side_effect=Exception("Calc tool error"))
    
    pipeline.registry.tools.clear()
    pipeline.registry.register(mock_calc)
    
    state = pipeline.build_initial_state(
        user_id="user-123",
        workspace_id="ws-abc",
        execution_id="exec-tool-fail",
        original_prompt="Calculate 250 * 12 mock",
        provider="mock"
    )
    
    final_state = await pipeline.execute(state)
    # Critic should retry, exceed 3 tool retries limit, and route to Response Generator (status FAILED)
    assert final_state["execution_status"] == ExecutionStatus.COMPLETED # Completes node path
    resp_val = json.loads(final_state["agent_outputs"]["ResponseGeneratorAgent"]["output"])
    assert resp_val["metadata"]["response_status"] == "FAILED"

@pytest.mark.asyncio
async def test_pipeline_research_retry_limit(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    # We want Critic to return RESEARCH_MORE
    # Mock execute of CriticAgent to always return RESEARCH_MORE
    from app.core.agent.base import AgentResult
    pipeline.critic.execute = AsyncMock(return_value=AgentResult(
        agent_name="CriticAgent",
        status="success",
        output=json.dumps({
            "execution_id": "exec-1",
            "decision": "RESEARCH_MORE",
            "overall_score": 0.5,
            "confidence": 0.9,
            "summary": "Need more data",
            "issues": []
        }),
        confidence=0.9,
        execution_time=0.05,
        token_usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    ))
    
    state = pipeline.build_initial_state(
        user_id="user-123",
        workspace_id="ws-abc",
        execution_id="exec-res-loop",
        original_prompt="Research data mock",
        provider="mock"
    )
    
    final_state = await pipeline.execute(state)
    # Verify metadata contains research_retries <= 3
    assert final_state["metadata"]["research_retries"] == 3

@pytest.mark.asyncio
async def test_pipeline_human_confirmation(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    # Weather tool requires confirmation
    state = pipeline.build_initial_state(
        user_id="user-123",
        workspace_id="ws-abc",
        execution_id="exec-weather",
        original_prompt="Get Seattle weather mock",
        provider="mock"
    )
    
    # Initially running executor pauses on WAITING_FOR_CONFIRMATION status
    final_state = await pipeline.execute(state)
    resp_obj = json.loads(final_state["agent_outputs"]["ResponseGeneratorAgent"]["output"])
    # ToolExecutor returns output status = requires_confirmation which Critic treats as FAIL if unconfirmed
    assert resp_obj["metadata"]["response_status"] == "FAILED"
    
    # Save step confirmation token
    token = json.loads(final_state["agent_outputs"]["ToolExecutorAgent"]["output"])["metadata"]["confirmation_token"]
    
    # Resume pipeline after confirmation
    resumed_state = await pipeline.resume_after_confirmation(
        execution_id="exec-weather", user_id="user-123", workspace_id="ws-abc", confirmation_token=token
    )
    # Succeeded execution
    final_resp = json.loads(resumed_state["agent_outputs"]["ResponseGeneratorAgent"]["output"])
    assert final_resp["metadata"]["response_status"] == "SUCCESS"

@pytest.mark.asyncio
async def test_pipeline_tenant_isolation(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    state = pipeline.build_initial_state(
        user_id="user-A",
        workspace_id="ws-A",
        execution_id="exec-isolated-1",
        original_prompt="Calculate 250 * 12 mock",
        provider="mock"
    )
    await pipeline.execute(state)
    
    # Attempting to load User A's checkpoint using User B's identity must raise error
    with pytest.raises(MemoryPermissionError):
        await pipeline.resume_execution("exec-isolated-1", user_id="user-B", workspace_id="ws-B")

@pytest.mark.asyncio
async def test_pipeline_cancellation(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    state = pipeline.build_initial_state(
        user_id="user-A",
        workspace_id="ws-A",
        execution_id="exec-cancel-1",
        original_prompt="Calculate mock",
        provider="mock"
    )
    await pipeline.execute(state)
    
    cancelled_state = await pipeline.cancel("exec-cancel-1", user_id="user-A", workspace_id="ws-A")
    assert cancelled_state["execution_status"] == ExecutionStatus.CANCELLED

@pytest.mark.asyncio
async def test_pipeline_concurrency(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    # Start two executions concurrently
    state_a = pipeline.build_initial_state("user-A", "ws-A", "exec-A", "Calculate 250 * 12 mock", provider="mock")
    state_b = pipeline.build_initial_state("user-B", "ws-B", "exec-B", "Research mock", provider="mock")
    
    res_a, res_b = await asyncio.gather(
        pipeline.execute(state_a),
        pipeline.execute(state_b)
    )
    
    # Verify separation
    assert res_a["user_id"] == "user-A"
    assert res_b["user_id"] == "user-B"
    assert "exec-A" in res_a["request_id"]
    assert "exec-B" in res_b["request_id"]

@pytest.mark.asyncio
async def test_pipeline_event_streaming(mock_ai_service):
    pipeline = AegisAIPipeline(mock_ai_service)
    
    state = pipeline.build_initial_state(
        user_id="user-123",
        workspace_id="ws-abc",
        execution_id="exec-stream-1",
        original_prompt="Calculate 250 * 12 mock",
        provider="mock"
    )
    
    events = []
    async for event in pipeline.stream(state):
        events.append(event)
        
    assert events[0]["event"] == "ExecutionStarted"
    assert any(e["event"] == "AgentCompleted" for e in events)
    assert events[-1]["event"] == "ExecutionCompleted"
