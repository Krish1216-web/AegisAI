import pytest
import uuid
import json
from unittest.mock import MagicMock, AsyncMock

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import ExecutionContext
from app.core.agent.rag import RAGAgent, RAGAgentResult, RAGAgentCitation
from app.core.agent.orchestrator import OrchestratorAgent, ExecutionPlan, AgentType, TaskType
from app.core.agent.planner import PlannerAgent, DetailedExecutionPlan, PlanStep
from app.core.agent.critic import CriticAgent, CriticDecision
from app.core.agent.response import ResponseGeneratorAgent, ResponseCitation
from app.core.agent.pipeline import AegisAIPipeline
from app.schemas.rag import RAGResponse, Citation, RetrievedChunk

@pytest.fixture
def mock_ai_service():
    service = MagicMock()
    service.redis = None
    service.generate_chat = AsyncMock()
    return service

@pytest.fixture
def base_state():
    return {
        "request_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
        "conversation_id": "conv-test-1",
        "original_prompt": "Summarize my uploaded quarterly report.",
        "current_task": None,
        "execution_status": ExecutionStatus.PENDING,
        "execution_plan": None,
        "detailed_execution_plan": None,
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "memory_context": None,
        "memory_results": None,
        "rag_result": None,
        "rag_context": None,
        "rag_citations": [],
        "rag_confidence": None,
        "graph_context": None,
        "research_results": None,
        "critic_result": None,
        "critic_decision": None,
        "quality_score": None,
        "final_response": None,
        "errors": [],
        "metadata": {"provider": "mock", "model": "mock-model"},
        "timestamps": {},
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "execution_time": 0.0,
        "confidence_score": 0.0,
        "current_agent": None,
        "retry_count": 0
    }

@pytest.fixture
def exec_context(base_state):
    return ExecutionContext(
        request_id=base_state["request_id"],
        user_id=base_state["user_id"],
        workspace_id=base_state["workspace_id"],
        conversation_id=base_state["conversation_id"],
        model="mock-model",
        provider="mock"
    )

# -----------------------------------------------------------------
# 1. RAG Agent Core Tests
# -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_agent_basic_mock_execution(mock_ai_service, base_state, exec_context):
    agent = RAGAgent(mock_ai_service)
    result = await agent.execute(base_state, exec_context)

    assert result.status == "success"
    assert result.agent_name == "RAGAgent"
    assert base_state["rag_result"] is not None
    assert base_state["rag_context"] is not None
    assert len(base_state["rag_citations"]) > 0
    assert base_state["rag_confidence"] >= 0.8
    assert base_state["execution_status"] == ExecutionStatus.RAG_RETRIEVAL

@pytest.mark.asyncio
async def test_rag_agent_no_evidence_behavior(mock_ai_service, base_state, exec_context):
    base_state["original_prompt"] = "What does the unknown nonexistent file say about aliens?"
    agent = RAGAgent(mock_ai_service)
    result = await agent.execute(base_state, exec_context)

    assert result.status in ["success", "warning"]
    assert len(base_state["rag_citations"]) == 0
    assert base_state["rag_confidence"] <= 0.3
    assert "couldn't find enough relevant information" in base_state["rag_context"]

def test_rag_agent_input_validation(mock_ai_service):
    agent = RAGAgent(mock_ai_service)
    assert agent.validate_input({"original_prompt": "valid query"}) is True
    assert agent.validate_input({"original_prompt": "", "messages": []}) is False

@pytest.mark.asyncio
async def test_rag_agent_with_real_rag_service(mock_ai_service, base_state):
    mock_rag_service = MagicMock()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_rag_service.query.return_value = RAGResponse(
        answer="AegisAI employs a multi-agent state graph with pgvector vector retrieval.",
        citations=[
            Citation(
                citation_number=1,
                document_id=doc_id,
                document_name="architecture_spec.pdf",
                page_number=2,
                section_title="System Architecture",
                snippet="AegisAI employs a multi-agent state graph with pgvector vector retrieval."
            )
        ],
        retrieved_chunks=[
            RetrievedChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                document_name="architecture_spec.pdf",
                chunk_index=0,
                content="AegisAI employs a multi-agent state graph with pgvector vector retrieval.",
                score=0.94,
                page_number=2,
                section_title="System Architecture"
            )
        ]
    )

    agent = RAGAgent(mock_ai_service, rag_service=mock_rag_service)
    context = ExecutionContext(
        request_id=base_state["request_id"],
        user_id=base_state["user_id"],
        workspace_id=base_state["workspace_id"],
        conversation_id=base_state["conversation_id"],
        model="gpt-4o-mini",
        provider="openai"
    )

    result = await agent.execute(base_state, context)

    assert result.status == "success"
    assert len(base_state["rag_citations"]) == 1
    assert base_state["rag_citations"][0]["document_id"] == str(doc_id)
    assert base_state["rag_citations"][0]["page_number"] == 2
    assert "pgvector" in base_state["rag_context"]

# -----------------------------------------------------------------
# 2. Orchestrator & Planner Integration Tests
# -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_classifies_rag_task(mock_ai_service, base_state, exec_context):
    base_state["original_prompt"] = "Summarize my uploaded project report and contract."
    orchestrator = OrchestratorAgent(mock_ai_service)
    result = await orchestrator.execute(base_state, exec_context)

    plan = ExecutionPlan.model_validate_json(result.output)
    assert plan.requires_rag is True
    assert AgentType.RAG in plan.required_agents
    assert plan.task_type == TaskType.DOCUMENT_ANALYSIS

@pytest.mark.asyncio
async def test_orchestrator_hybrid_rag_and_research(mock_ai_service, base_state, exec_context):
    base_state["original_prompt"] = "Compare my uploaded report with latest industry research on AI."
    orchestrator = OrchestratorAgent(mock_ai_service)
    result = await orchestrator.execute(base_state, exec_context)

    plan = ExecutionPlan.model_validate_json(result.output)
    assert plan.requires_rag is True
    assert plan.requires_research is True
    assert AgentType.RAG in plan.required_agents
    assert AgentType.RESEARCH in plan.required_agents
    assert plan.task_type == TaskType.MIXED_TASK

@pytest.mark.asyncio
async def test_planner_schedules_rag_step(mock_ai_service, base_state, exec_context):
    base_state["agent_outputs"]["OrchestratorAgent"] = {
        "output": json.dumps({
            "task_type": "DOCUMENT_ANALYSIS",
            "complexity": "SIMPLE",
            "goal": "Analyze document",
            "steps": ["Retrieve doc"],
            "required_agents": ["RAG", "RESPONSE_GENERATOR"],
            "parallelizable_steps": [],
            "requires_memory": False,
            "requires_rag": True,
            "requires_research": False,
            "requires_tools": False,
            "requires_critic": False,
            "requires_human_confirmation": False,
            "requires_clarification": False,
            "confidence": 0.95
        })
    }

    planner = PlannerAgent(mock_ai_service)
    result = await planner.execute(base_state, exec_context)

    plan = DetailedExecutionPlan.model_validate_json(result.output)
    rag_steps = [s for s in plan.steps if s.agent_type == AgentType.RAG]
    assert len(rag_steps) == 1
    assert rag_steps[0].action == "retrieve_and_answer"

# -----------------------------------------------------------------
# 3. Critic Citation Integrity & Security Tests
# -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_critic_validates_rag_citations_success(mock_ai_service, base_state, exec_context):
    doc_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    base_state["rag_result"] = {"query": "test", "answer": "Grounded answer"}
    base_state["rag_citations"] = [
        {
            "citation_id": f"chunk_{chunk_id}",
            "source_type": "document",
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "document_name": "Report.pdf",
            "page_number": 1,
            "snippet": "Revenue grew by 24%."
        }
    ]

    critic = CriticAgent(mock_ai_service)
    result = await critic.execute(base_state, exec_context)

    assert result.status == "success"
    c_res = json.loads(result.output)
    assert c_res["decision"] == CriticDecision.ACCEPT.value

@pytest.mark.asyncio
async def test_critic_rejects_fabricated_rag_citations(mock_ai_service, base_state, exec_context):
    base_state["rag_result"] = {"query": "test", "answer": "Hallucinated answer"}
    base_state["rag_citations"] = [
        {
            "citation_id": "chunk_fake",
            "source_type": "document",
            "document_id": "invalid_fabricated_doc_id",
            "chunk_id": "invalid_fabricated_chunk_id",
            "document_name": "Ghost_Doc.pdf"
        }
    ]

    critic = CriticAgent(mock_ai_service)
    result = await critic.execute(base_state, exec_context)

    assert result.status == "failed"
    c_res = json.loads(result.output)
    assert c_res["decision"] == CriticDecision.FAIL.value
    assert any(i["issue_id"] == "fabricated_citation" for i in c_res["issues"])

@pytest.mark.asyncio
async def test_critic_rejects_cross_tenant_rag_citations(mock_ai_service, base_state):
    exec_context_b = ExecutionContext(
        request_id=base_state["request_id"],
        user_id="user-B",
        workspace_id="ws-B",
        conversation_id="conv-B",
        model="mock-model",
        provider="mock"
    )

    base_state["rag_result"] = {"query": "test", "answer": "Leaked context"}
    base_state["rag_citations"] = [
        {
            "citation_id": "chunk_1",
            "source_type": "document",
            "document_id": "doc-tenant-a",
            "chunk_id": "chunk-tenant-a",
            "document_name": "tenant-a_secret.pdf"
        }
    ]

    critic = CriticAgent(mock_ai_service)
    result = await critic.execute(base_state, exec_context_b)

    assert result.status == "failed"
    c_res = json.loads(result.output)
    assert c_res["decision"] == CriticDecision.FAIL.value

# -----------------------------------------------------------------
# 4. Response Generator Multi-Source Synthesis Tests
# -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_generator_dual_citations_rag_and_research(mock_ai_service, base_state, exec_context):
    doc_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    
    # 1. Critic passes
    base_state["agent_outputs"]["CriticAgent"] = {
        "output": json.dumps({"decision": "ACCEPT", "overall_score": 1.0})
    }

    # 2. RAG data
    base_state["rag_context"] = "Quarterly revenue grew by 24%."
    base_state["rag_citations"] = [
        {
            "citation_id": f"chunk_{chunk_id}",
            "source_type": "document",
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "document_name": "Q2_Report.pdf",
            "page_number": 3,
            "snippet": "Quarterly revenue grew by 24%."
        }
    ]

    # 3. Web Research data
    base_state["research_results"] = json.dumps({
        "summary": "Industry growth averaged 18% in 2026.",
        "findings": [],
        "sources": [
            {
                "source_id": "src_industry_1",
                "title": "Global Tech Market Report 2026",
                "url": "https://industry-analytics.org/2026",
                "publisher": "TechAnalytica",
                "published_at": "2026-06-01",
                "content_reference": "Tech sector grew by 18%."
            }
        ]
    })

    # 4. Memory context
    base_state["memory_context"] = "User preference: Concise executive summaries."

    response_gen = ResponseGeneratorAgent(mock_ai_service)
    result = await response_gen.execute(base_state, exec_context)

    assert result.status == "success"
    r_data = json.loads(result.output)
    assert len(r_data["citations"]) == 2

    # Verify both citation source types exist
    doc_cites = [c for c in r_data["citations"] if c["source_type"] == "document"]
    res_cites = [c for c in r_data["citations"] if c["source_type"] == "research"]
    assert len(doc_cites) == 1
    assert doc_cites[0]["document_id"] == doc_id
    assert doc_cites[0]["page_number"] == 3
    assert len(res_cites) == 1
    assert res_cites[0]["source_id"] == "src_industry_1"

    # Verify synthesized content contains all parts
    assert "Document Knowledge" in r_data["content"]
    assert "Concise executive summaries" in r_data["content"]

# -----------------------------------------------------------------
# 5. Full Pipeline End-to-End Execution with RAG
# -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_pipeline_rag_execution(mock_ai_service):
    pipeline = AegisAIPipeline(ai_service=mock_ai_service)
    
    initial_state = pipeline.build_initial_state(
        user_id=str(uuid.uuid4()),
        workspace_id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        original_prompt="Summarize my uploaded quarterly report with calculations.",
        provider="mock",
        model="mock"
    )

    final_state = await pipeline.execute(initial_state)

    assert final_state["execution_status"] == ExecutionStatus.COMPLETED
    assert final_state["final_response"] is not None
    assert "RAGAgent" in final_state["agent_outputs"]
    assert "CriticAgent" in final_state["agent_outputs"]
    assert "ResponseGeneratorAgent" in final_state["agent_outputs"]
    assert len(final_state["rag_citations"]) > 0

@pytest.mark.asyncio
async def test_full_pipeline_rag_streaming(mock_ai_service):
    pipeline = AegisAIPipeline(ai_service=mock_ai_service)
    
    initial_state = pipeline.build_initial_state(
        user_id=str(uuid.uuid4()),
        workspace_id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        original_prompt="Analyze my contract document.",
        provider="mock",
        model="mock"
    )

    events = []
    async for event in pipeline.stream(initial_state):
        events.append(event)

    assert len(events) >= 3
    assert any(e.get("event") == "ExecutionStarted" for e in events)
    assert any(e.get("event") == "ExecutionCompleted" for e in events)
