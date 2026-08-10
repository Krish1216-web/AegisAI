import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import time

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.orchestrator import ExecutionPlan, TaskType, Complexity, AgentType
from app.core.agent.planner import DetailedExecutionPlan, PlanStep
from app.core.agent.research import (
    ResearchAgent, ResearchRequest, ResearchResult, ResearchFinding, ResearchSource, MockResearchProvider
)
from app.core.agent.exceptions import NoResultsFound, InvalidResearchResult
from app.core.ai.base import ChatResponse, TokenUsage
from app.services.ai_service import AIService

@pytest.fixture
def mock_ai_service():
    return MagicMock(spec=AIService)

@pytest.fixture
def mock_provider():
    return MockResearchProvider()

@pytest.mark.asyncio
async def test_research_mock_provider_search(mock_provider):
    sources = await mock_provider.search("Query trends")
    assert len(sources) == 1
    assert sources[0].source_id == "mock_src_1"
    assert "Blockchain" in sources[0].title

@pytest.mark.asyncio
async def test_research_agent_mock_run(mock_ai_service, mock_provider):
    agent = ResearchAgent(mock_ai_service, mock_provider)
    
    state: AgentState = {
        "original_prompt": "Research mock blockchain trends",
        "messages": [],
        "agent_outputs": {},
        "token_usage": {},
        "metadata": {}
    }
    context = ExecutionContext(
        request_id="req-1", user_id="u-1", workspace_id="w-1", conversation_id="c-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = ResearchResult.model_validate_json(result.output)
    assert parsed.query == "Research mock blockchain trends"
    assert parsed.findings[0].source_ids == ["mock_src_1"]

@pytest.mark.asyncio
async def test_research_evidence_linking_failure(mock_ai_service, mock_provider):
    # If LLM invents a source ID that was not retrieved, raise InvalidResearchResult
    agent = ResearchAgent(mock_ai_service, mock_provider)
    
    result_with_invented_source = ResearchResult(
        query="blockchain",
        summary="summary",
        findings=[
            ResearchFinding(
                finding_id="f1", title="title", claim="claim", supporting_evidence="evidence",
                source_ids=["non_existent_source_id"], confidence=0.9, relevance=0.9, timestamp="2026-08-10"
            )
        ],
        sources=[], # no sources matched
        confidence=0.9,
        research_time=0.1,
        source_count=0
    )
    
    mock_ai_service.generate_chat = AsyncMock(return_value=ChatResponse(
        content=result_with_invented_source.model_dump_json(),
        model="gpt-4o-mini",
        provider="openai",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        latency_ms=100
    ))
    
    state: AgentState = {
        "original_prompt": "blockchain",
        "messages": [],
        "agent_outputs": {},
        "token_usage": {},
        "metadata": {}
    }
    context = ExecutionContext(
        request_id="req-1", user_id="u-1", workspace_id="w-1", conversation_id="c-1",
        permissions=["read"], model="gpt-4", provider="openai"
    )
    
    with pytest.raises(InvalidResearchResult):
        await agent.execute(state, context)

@pytest.mark.asyncio
async def test_orchestrator_planner_research_integration(mock_ai_service, mock_provider):
    # Integration test showing state flow:
    # Orchestrator outputs Plan -> Planner parses Plan steps -> Research runs search step
    orch_plan = ExecutionPlan(
        task_type=TaskType.RESEARCH,
        complexity=Complexity.SIMPLE,
        goal="Collect blockchain notes",
        steps=["Search papers"],
        required_agents=[AgentType.RESEARCH],
        confidence=0.9
    )
    
    planner_plan = DetailedExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1", title="Research latest papers", description="Fetch papers",
                agent_type=AgentType.RESEARCH, action="search", expected_output="blockchain data"
            )
        ]
    )
    
    agent = ResearchAgent(mock_ai_service, mock_provider)
    
    state: AgentState = {
        "original_prompt": "Research mock blockchain trends",
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
        request_id="req-1", user_id="u-1", workspace_id="w-1", conversation_id="c-1",
        permissions=["read"], model="gpt-4", provider="mock"
    )
    
    result = await agent.execute(state, context)
    assert result.status == "success"
    
    parsed = ResearchResult.model_validate_json(result.output)
    assert len(parsed.findings) == 1
    assert parsed.findings[0].source_ids == ["mock_src_1"]
