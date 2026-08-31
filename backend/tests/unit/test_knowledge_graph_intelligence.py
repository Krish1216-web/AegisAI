import pytest
import uuid
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import get_db
from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService, NodeNotFound, EdgeNotFound
from app.services.knowledge_graph_intelligence import KnowledgeGraphIntelligenceService
from app.core.agent.rag import RAGAgent
from app.core.agent.base import ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.services.ai_service import AIService
from app.schemas.knowledge_graph import (
    NodeCreate,
    EdgeCreate,
    PathSearchRequest,
    RelationshipAnalysisRequest,
    GraphIntelligenceContextRequest
)

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

    # Seed Organization & Role
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Intelligence Org")
    session.add(org)

    role_id = uuid.uuid4()
    role = Role(id=role_id, name="member")
    session.add(role)
    session.commit()

    # Seed User 1 (Tenant 1)
    user_id_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_1 = User(
        id=user_id_1,
        email="user1@aegis.ai",
        username="user1",
        password_hash="hash1",
        role_id=role_id,
        is_active=True
    )
    session.add(user_1)

    # Seed User 2 (Tenant 2)
    user_id_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_2 = User(
        id=user_id_2,
        email="user2@aegis.ai",
        username="user2",
        password_hash="hash2",
        role_id=role_id,
        is_active=True
    )
    session.add(user_2)

    # Seed Workspace 1 (Tenant 1)
    ws_id_1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    ws_1 = Workspace(id=ws_id_1, organization_id=org_id, name="Workspace Alpha")
    session.add(ws_1)

    # Seed Workspace 2 (Tenant 2)
    ws_id_2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    ws_2 = Workspace(id=ws_id_2, organization_id=org_id, name="Workspace Beta")
    session.add(ws_2)

    session.commit()

    try:
        yield session
    finally:
        session.close()

def build_sample_graph(db, user_id, workspace_id):
    """
    Constructs a sample enterprise graph:
    Project -> contains -> Document -> contains -> Chunk
    Project -> uses -> Skill (Python)
    Project -> assigned_to -> Agent
    """
    service = KnowledgeGraphService(db)

    n_proj = service.create_node(
        user_id=user_id,
        workspace_id=workspace_id,
        node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="AegisAI Core", description="Primary AI Engine")
    )
    n_doc = service.create_node(
        user_id=user_id,
        workspace_id=workspace_id,
        node_data=NodeCreate(node_type=NodeType.DOCUMENT.value, name="Architecture Spec", description="System blueprints")
    )
    n_chunk = service.create_node(
        user_id=user_id,
        workspace_id=workspace_id,
        node_data=NodeCreate(node_type=NodeType.DOCUMENT_CHUNK.value, name="Chunk #1", description="LangGraph pipeline chunk")
    )
    n_skill = service.create_node(
        user_id=user_id,
        workspace_id=workspace_id,
        node_data=NodeCreate(node_type=NodeType.SKILL.value, name="Python SDK", description="Core Python utilities")
    )
    n_agent = service.create_node(
        user_id=user_id,
        workspace_id=workspace_id,
        node_data=NodeCreate(node_type=NodeType.AGENT.value, name="Orchestrator Agent", description="Central dispatcher")
    )

    # Edges
    service.create_edge(user_id=user_id, workspace_id=workspace_id, edge_data=EdgeCreate(
        source_node_id=n_proj.id, target_node_id=n_doc.id, relationship_type=RelationshipType.CONTAINS.value, confidence=1.0
    ))
    service.create_edge(user_id=user_id, workspace_id=workspace_id, edge_data=EdgeCreate(
        source_node_id=n_doc.id, target_node_id=n_chunk.id, relationship_type=RelationshipType.CONTAINS.value, confidence=0.95
    ))
    service.create_edge(user_id=user_id, workspace_id=workspace_id, edge_data=EdgeCreate(
        source_node_id=n_proj.id, target_node_id=n_skill.id, relationship_type=RelationshipType.USES.value, confidence=0.9
    ))
    service.create_edge(user_id=user_id, workspace_id=workspace_id, edge_data=EdgeCreate(
        source_node_id=n_proj.id, target_node_id=n_agent.id, relationship_type=RelationshipType.ASSIGNED_TO.value, confidence=0.85
    ))

    return n_proj, n_doc, n_chunk, n_skill, n_agent

def test_related_entity_discovery_and_ranking(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    n_proj, n_doc, n_chunk, n_skill, n_agent = build_sample_graph(db_session, user_id, ws_id)

    intel_service = KnowledgeGraphIntelligenceService(db_session)
    resp = intel_service.get_related_entities(
        user_id=user_id,
        workspace_id=ws_id,
        node_id=n_proj.id,
        depth=2,
        limit=10
    )

    assert resp.node_id == n_proj.id
    assert resp.total_related >= 4
    entity_names = [e.name for e in resp.related_entities]
    assert "Architecture Spec" in entity_names
    assert "Chunk #1" in entity_names
    assert "Python SDK" in entity_names
    assert "Orchestrator Agent" in entity_names

    # Check that 1-hop document has higher relevance than 2-hop chunk
    doc_item = next(e for e in resp.related_entities if e.name == "Architecture Spec")
    chunk_item = next(e for e in resp.related_entities if e.name == "Chunk #1")
    assert doc_item.distance == 1
    assert chunk_item.distance == 2
    assert doc_item.relevance_score > chunk_item.relevance_score

def test_shortest_path_direct_and_multihop(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    n_proj, n_doc, n_chunk, n_skill, n_agent = build_sample_graph(db_session, user_id, ws_id)

    intel_service = KnowledgeGraphIntelligenceService(db_session)

    # 1. Direct path: Project -> Document
    path_direct = intel_service.find_shortest_path(
        user_id=user_id,
        workspace_id=ws_id,
        source_node_id=n_proj.id,
        target_node_id=n_doc.id
    )
    assert path_direct.path_found is True
    assert path_direct.distance == 1
    assert len(path_direct.steps) == 1
    assert path_direct.steps[0].relationship_type == RelationshipType.CONTAINS.value

    # 2. Multihop path: Project -> Document -> Chunk
    path_multihop = intel_service.find_shortest_path(
        user_id=user_id,
        workspace_id=ws_id,
        source_node_id=n_proj.id,
        target_node_id=n_chunk.id
    )
    assert path_multihop.path_found is True
    assert path_multihop.distance == 2
    assert len(path_multihop.steps) == 2
    assert len(path_multihop.nodes) == 3

    # 3. Same node
    path_same = intel_service.find_shortest_path(
        user_id=user_id,
        workspace_id=ws_id,
        source_node_id=n_proj.id,
        target_node_id=n_proj.id
    )
    assert path_same.path_found is True
    assert path_same.distance == 0

def test_cycle_safe_pathfinding(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = KnowledgeGraphService(db_session)

    n_a = service.create_node(user_id=user_id, workspace_id=ws_id, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node A"))
    n_b = service.create_node(user_id=user_id, workspace_id=ws_id, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node B"))
    n_c = service.create_node(user_id=user_id, workspace_id=ws_id, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node C"))
    n_d = service.create_node(user_id=user_id, workspace_id=ws_id, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node D"))

    # Create cyclic graph: A -> B -> C -> D and D -> B (subcycle)
    service.create_edge(user_id=user_id, workspace_id=ws_id, edge_data=EdgeCreate(source_node_id=n_a.id, target_node_id=n_b.id, relationship_type="DEPENDS_ON"))
    service.create_edge(user_id=user_id, workspace_id=ws_id, edge_data=EdgeCreate(source_node_id=n_b.id, target_node_id=n_c.id, relationship_type="DEPENDS_ON"))
    service.create_edge(user_id=user_id, workspace_id=ws_id, edge_data=EdgeCreate(source_node_id=n_c.id, target_node_id=n_d.id, relationship_type="DEPENDS_ON"))
    service.create_edge(user_id=user_id, workspace_id=ws_id, edge_data=EdgeCreate(source_node_id=n_d.id, target_node_id=n_b.id, relationship_type="DEPENDS_ON"))

    intel_service = KnowledgeGraphIntelligenceService(db_session)
    path = intel_service.find_shortest_path(user_id=user_id, workspace_id=ws_id, source_node_id=n_a.id, target_node_id=n_d.id)

    assert path.path_found is True
    assert path.distance == 2
    assert len(path.steps) == 2

def test_relationship_analysis(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    n_proj, n_doc, n_chunk, n_skill, n_agent = build_sample_graph(db_session, user_id, ws_id)

    intel_service = KnowledgeGraphIntelligenceService(db_session)
    analysis = intel_service.analyze_relationships(
        user_id=user_id,
        workspace_id=ws_id,
        source_node_id=n_proj.id,
        target_node_id=n_chunk.id
    )

    assert analysis.are_connected is True
    assert analysis.min_distance == 2
    assert len(analysis.indirect_relationships) == 1
    assert "Architecture Spec" in analysis.indirect_relationships[0].via_nodes
    assert "Indirectly connected" in analysis.summary

def test_build_graph_context_formatting(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    n_proj, n_doc, n_chunk, n_skill, n_agent = build_sample_graph(db_session, user_id, ws_id)

    intel_service = KnowledgeGraphIntelligenceService(db_session)
    context_str = intel_service.build_graph_context(
        user_id=user_id,
        workspace_id=ws_id,
        entity_names=["AegisAI Core"],
        depth=2,
        max_entities=10
    )

    assert "=== KNOWLEDGE GRAPH RELATIONSHIPS ===" in context_str
    assert "AegisAI Core [PROJECT]" in context_str
    assert "Architecture Spec [DOCUMENT]" in context_str
    assert "Python SDK [SKILL]" in context_str

def test_tenant_isolation_in_graph_intelligence(db_session):
    user_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    n_proj1, _, _, _, _ = build_sample_graph(db_session, user_1, ws_1)

    user_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ws_2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    n_proj2, _, _, _, _ = build_sample_graph(db_session, user_2, ws_2)

    intel_service = KnowledgeGraphIntelligenceService(db_session)

    # User 2 cannot explore User 1's node
    with pytest.raises(NodeNotFound):
        intel_service.get_related_entities(
            user_id=user_2,
            workspace_id=ws_2,
            node_id=n_proj1.id
        )

    # User 1 cannot pathfind to User 2's node
    with pytest.raises(NodeNotFound):
        intel_service.find_shortest_path(
            user_id=user_1,
            workspace_id=ws_1,
            source_node_id=n_proj1.id,
            target_node_id=n_proj2.id
        )

def test_enhanced_graph_search(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    build_sample_graph(db_session, user_id, ws_id)

    intel_service = KnowledgeGraphIntelligenceService(db_session)

    # Search by text query
    results = intel_service.enhanced_graph_search(
        user_id=user_id,
        workspace_id=ws_id,
        query="Architecture",
        depth=1,
        limit=10
    )
    assert len(results) >= 1
    assert any(r.name == "Architecture Spec" for r in results)

    # Search by node_type
    proj_results = intel_service.enhanced_graph_search(
        user_id=user_id,
        workspace_id=ws_id,
        node_type=NodeType.PROJECT.value,
        depth=0,
        limit=5
    )
    assert len(proj_results) == 1
    assert proj_results[0].name == "AegisAI Core"

@pytest.mark.asyncio
async def test_rag_agent_kg_intelligence_integration(db_session):
    user_id = "11111111-1111-1111-1111-111111111111"
    ws_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    build_sample_graph(db_session, uuid.UUID(user_id), uuid.UUID(ws_id))

    mock_ai = MagicMock(spec=AIService)
    rag_agent = RAGAgent(ai_service=mock_ai, db=db_session)

    state: AgentState = {
        "user_id": user_id,
        "workspace_id": ws_id,
        "original_prompt": "What does the Architecture Spec document contain?",
        "messages": [],
        "agent_outputs": {}
    }
    context = ExecutionContext(
        request_id="req-1234",
        user_id=user_id,
        workspace_id=ws_id,
        conversation_id="conv-5678",
        model="gpt-4o-mini",
        provider="mock"
    )

    result = await rag_agent.execute(state, context)
    assert result.status == "success"
    assert "rag_result" in state
    assert state["rag_result"] is not None
