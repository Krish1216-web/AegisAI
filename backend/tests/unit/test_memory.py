import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import time

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.orchestrator import ExecutionPlan, TaskType, Complexity, AgentType
from app.core.agent.planner import DetailedExecutionPlan, PlanStep
from app.core.agent.memory import (
    MemoryAgent, MemoryRecord, MemoryQuery, MemoryResult, MemoryType, MockMemoryProvider, scrub_sensitive_data
)
from app.core.agent.exceptions import MemoryPermissionError
from app.core.ai.base import ChatResponse, TokenUsage
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    return MagicMock(spec=AIService)

@pytest.fixture
def mock_provider():
    return MockMemoryProvider()

def test_sensitive_data_filtering():
    raw_content = "My admin password is 'Secret123!' and the OpenAI API key is sk-1234567890abcdef1234567890abcdef"
    cleaned = scrub_sensitive_data(raw_content)
    assert "Secret123!" not in cleaned
    assert "sk-1234" not in cleaned
    assert "password" in cleaned
    assert "[REDACTED_SECRET]" in cleaned

@pytest.mark.asyncio
async def test_memory_user_and_workspace_isolation(mock_provider):
    # Setup Query for User A, Workspace A
    query_ok = MemoryQuery(
        query="*", user_id="user-A", workspace_id="ws-A"
    )
    res_ok = await mock_provider.search(query_ok)
    assert len(res_ok) == 1
    assert res_ok[0].content == "User A coding preferences: prefers Java examples."

    # Setup cross-tenant query attempting to query User B's workspace from User A
    query_bad = MemoryQuery(
        query="*", user_id="user-A", workspace_id="ws-B"
    )
    res_bad = await mock_provider.search(query_bad)
    assert len(res_bad) == 0 # returns empty, completely isolated

@pytest.mark.asyncio
async def test_memory_crud_permission_check(mock_provider):
    retrieved_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Store record
    record = MemoryRecord(
        memory_id="mem_test", user_id="user-A", workspace_id="ws-A",
        memory_type=MemoryType.LEARNING, content="Learned calculus",
        source="book", importance=0.5, confidence=0.8, created_at=retrieved_time, updated_at=retrieved_time
    )
    await mock_provider.store(record)

    # Get from correct tenant
    retrieved = await mock_provider.get("mem_test", "user-A", "ws-A")
    assert retrieved is not None
    assert retrieved.content == "Learned calculus"

    # Block retrieval from incorrect tenant
    with pytest.raises(MemoryPermissionError):
        await mock_provider.get("mem_test", "user-B", "ws-A")

    # Block delete from incorrect tenant
    with pytest.raises(MemoryPermissionError):
        await mock_provider.delete("mem_test", "user-A", "ws-B")

@pytest.mark.asyncio
async def test_memory_agent_mock_run(mock_ai_service, mock_provider):
    agent = MemoryAgent(mock_ai_service, mock_provider)
    
    state: AgentState = {
        "original_prompt": "What are my coding preferences?",
        "messages": [],
        "agent_outputs": {},
        "token_usage": {},
        "metadata": {}
    }
    
    context = ExecutionContext(
        request_id="req-1", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = MemoryResult.model_validate_json(result.output)
    assert parsed.memory_count == 1
    assert parsed.memories[0].user_id == "user-A"

@pytest.mark.asyncio
async def test_orchestrator_planner_memory_integration(mock_ai_service, mock_provider):
    # Integration test showing state flow:
    # Orchestrator outputs Plan -> Planner parses Plan steps -> Memory Agent retrieves notes
    orch_plan = ExecutionPlan(
        task_type=TaskType.MEMORY_QUERY,
        complexity=Complexity.SIMPLE,
        goal="Query preferences",
        steps=["Retrieve preference memory"],
        required_agents=[AgentType.MEMORY],
        confidence=0.9
    )
    
    planner_plan = DetailedExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1", title="Query preferences", description="Retrieve memory",
                agent_type=AgentType.MEMORY, action="search", expected_output="preference details"
            )
        ]
    )
    
    agent = MemoryAgent(mock_ai_service, mock_provider)
    
    state: AgentState = {
        "original_prompt": "preferences",
        "messages": [],
        "agent_outputs": {
            "OrchestratorAgent": {
                "output": orch_plan.model_dump_json()
            },
            "PlannerAgent": {
                "output": planner_plan.model_dump_json()
            }
        },
        "token_usage": {},
        "metadata": {}
    }
    
    context = ExecutionContext(
        request_id="req-1", user_id="user-A", workspace_id="ws-A", conversation_id="conv-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = MemoryResult.model_validate_json(result.output)
    assert len(parsed.memories) == 1
    assert parsed.memories[0].user_id == "user-A"
