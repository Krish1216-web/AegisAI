import pytest
import uuid
import json
from unittest.mock import MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.core.agent.graph_reasoning import GraphReasoningAgent
from app.core.agent.orchestrator import OrchestratorAgent, TaskType, AgentType
from app.core.agent.critic import CriticAgent, CriticDecision
from app.core.agent.response import ResponseGeneratorAgent
from app.core.agent.pipeline import AegisAIPipeline
from app.core.agent.base import ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.services.ai_service import AIService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=uuid.uuid4(), name="Reasoning Test Org")
    session.add(org)
    role = Role(id=uuid.uuid4(), name="member")
    session.add(role)
    session.commit()

    u1 = User(id=uuid.UUID("11111111-1111-1111-1111-111111111111"), email="u1@aegis.ai", username="u1", password_hash="h", role_id=role.id)
    ws1 = Workspace(id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), organization_id=org.id, name="WS 1")
    session.add_all([u1, ws1])

    u2 = User(id=uuid.UUID("22222222-2222-2222-2222-222222222222"), email="u2@aegis.ai", username="u2", password_hash="h", role_id=role.id)
    ws2 = Workspace(id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), organization_id=org.id, name="WS 2")
    session.add_all([u2, ws2])

    session.commit()

    try:
        yield session
    finally:
        session.close()

def make_context(request_id="req-1", user_id="u1", workspace_id="ws1", prompt="", db=None):
    return ExecutionContext(
        request_id=request_id,
        user_id=user_id,
        workspace_id=workspace_id,
        conversation_id="conv-1",
        permissions=[],
        model="gpt-4o-mini",
        provider="mock",
        configuration={"prompt": prompt, "db": db}
    )

@pytest.mark.asyncio
async def test_graph_reasoning_agent_execution(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    n1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="AegisAI Core", node_type="PROJECT")
    n2 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="PostgreSQL Engine", node_type="SKILL")
    db_session.add_all([n1, n2])
    db_session.commit()

    e1 = KnowledgeGraphEdge(
        id=uuid.uuid4(), user_id=u1, workspace_id=ws1,
        source_node_id=n1.id, target_node_id=n2.id,
        relationship_type="USES", confidence=0.98
    )
    db_session.add(e1)
    db_session.commit()

    ai_service = MagicMock(spec=AIService)
    agent = GraphReasoningAgent(ai_service, db=db_session)
    prompt = "How is AegisAI Core related to PostgreSQL Engine?"
    state = AgentState(
        original_prompt=prompt,
        user_id=str(u1),
        workspace_id=str(ws1),
        messages=[{"role": "user", "content": prompt}],
        agent_outputs={},
        metadata={}
    )
    context = make_context(request_id="test-req-1", user_id=str(u1), workspace_id=str(ws1), prompt=prompt, db=db_session)

    result = await agent.execute(state, context)
    assert result.status == "completed"
    parsed = json.loads(result.output)
    assert parsed["matched_nodes_count"] >= 2
    assert parsed["matched_edges_count"] >= 1
    assert len(parsed["citations"]) >= 2
    assert parsed["citations"][0]["source_type"] in ("graph", "graph_edge")

@pytest.mark.asyncio
async def test_orchestrator_graph_classification():
    ai_service = MagicMock(spec=AIService)
    orchestrator = OrchestratorAgent(ai_service)
    prompt = "Show the graph dependency chain between Auth and Database (mock)"
    state = AgentState(
        original_prompt=prompt,
        messages=[{"role": "user", "content": prompt}],
        agent_outputs={},
        metadata={}
    )
    context = make_context(request_id="test-orch", prompt=prompt)

    result = await orchestrator.execute(state, context)
    assert result.status == "success"
    plan = json.loads(result.output)
    assert plan["requires_graph"] is True
    assert AgentType.GRAPH in plan["required_agents"]
    assert plan["task_type"] == TaskType.GRAPH_QUERY

@pytest.mark.asyncio
async def test_critic_graph_citation_validation():
    ai_service = MagicMock(spec=AIService)
    critic = CriticAgent(ai_service)
    
    # Valid graph citation
    valid_state = AgentState(
        original_prompt="Graph query mock",
        graph_citations=[{"source_type": "graph", "node_id": str(uuid.uuid4()), "node_name": "ValidNode"}],
        agent_outputs={},
        metadata={}
    )
    context = make_context(request_id="crit-1", prompt="Graph query mock")
    res_valid = await critic.execute(valid_state, context)
    crit_valid = json.loads(res_valid.output)
    assert crit_valid["decision"] == "ACCEPT"

    # Fabricated graph citation
    invalid_state = AgentState(
        original_prompt="Graph query mock",
        graph_citations=[{"source_type": "graph", "node_id": "fabricated-node-999", "node_name": "FakeNode"}],
        agent_outputs={},
        metadata={}
    )
    res_invalid = await critic.execute(invalid_state, context)
    crit_invalid = json.loads(res_invalid.output)
    assert crit_invalid["decision"] == "FAIL"

@pytest.mark.asyncio
async def test_response_generator_graph_citations():
    ai_service = MagicMock(spec=AIService)
    resp_gen = ResponseGeneratorAgent(ai_service)
    node_id = str(uuid.uuid4())
    
    state = AgentState(
        original_prompt="Summarize graph mock",
        graph_context="=== KNOWLEDGE GRAPH TOPOLOGY ===\n- Project (AegisAI) USES Skill (Python)",
        graph_citations=[{"source_type": "graph", "node_id": node_id, "node_name": "AegisAI", "node_type": "PROJECT"}],
        agent_outputs={"CriticAgent": {"output": json.dumps({"decision": "ACCEPT"})}},
        metadata={}
    )
    context = make_context(request_id="resp-1", prompt="Summarize graph mock")
    
    result = await resp_gen.execute(state, context)
    assert result.status == "success"
    output = json.loads(result.output)
    assert "Knowledge Graph Topology" in output["content"]
    assert len(output["citations"]) >= 1
    assert output["citations"][0]["source_type"] == "knowledge_graph"

@pytest.mark.asyncio
async def test_full_pipeline_with_graph_reasoning(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    n1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Project Alpha", node_type="PROJECT")
    db_session.add(n1)
    db_session.commit()

    ai_service = MagicMock(spec=AIService)
    pipeline = AegisAIPipeline(ai_service=ai_service, db=db_session)
    
    prompt = "Show the knowledge graph connections for Project Alpha mock"
    initial_state = pipeline.build_initial_state(
        user_id=str(u1),
        workspace_id=str(ws1),
        execution_id="pipe-graph-1",
        original_prompt=prompt,
        provider="mock"
    )

    final_state = await pipeline.execute(initial_state)
    assert final_state.get("execution_status") == ExecutionStatus.COMPLETED
    assert "final_response" in final_state
    assert final_state["final_response"] is not None
