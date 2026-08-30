import pytest
import uuid
import asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.document import Document, DocumentChunk
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.core.rag.hybrid import (
    HybridRetrievedItem,
    HybridFusionConfig,
    HybridRAGResult,
    QueryEntityExtractor,
    HybridScoreFusion,
    HybridContextBuilder,
    HybridRAGService,
    HybridRAGFactory
)
from app.core.agent.rag import RAGAgent
from app.core.agent.base import ExecutionContext

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

    # Seed Org & Role
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Hybrid Org")
    session.add(org)

    role_id = uuid.uuid4()
    role = Role(id=role_id, name="member")
    session.add(role)
    session.commit()

    # Seed User 1 (Tenant 1)
    user_id_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_1 = User(
        id=user_id_1,
        email="u1@aegis.ai",
        username="u1",
        password_hash="hash1",
        role_id=role_id,
        is_active=True
    )
    session.add(user_1)

    # Seed User 2 (Tenant 2)
    user_id_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user_2 = User(
        id=user_id_2,
        email="u2@aegis.ai",
        username="u2",
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

def test_query_entity_extractor():
    q1 = "What does AegisAI use for database storage with PostgreSQL and FastAPI?"
    entities1 = QueryEntityExtractor.extract_query_entities(q1)
    assert "AegisAI" in entities1
    assert "PostgreSQL" in entities1
    assert "FastAPI" in entities1

    intent1 = QueryEntityExtractor.analyze_query_intent(q1)
    assert intent1["has_graph_intent"] is True
    assert intent1["strategy"] in ("graph_centric", "hybrid")

    q2 = "Summarize the uploaded contract pdf on page 2"
    intent2 = QueryEntityExtractor.analyze_query_intent(q2)
    assert intent2["has_doc_intent"] is True

def test_hybrid_score_fusion_and_deduplication():
    fusion = HybridScoreFusion(HybridFusionConfig(vector_weight=0.6, graph_weight=0.3, metadata_weight=0.1))
    
    chunk_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_chunk = MagicMock(
        id=chunk_id,
        document_id=doc_id,
        content="AegisAI utilizes PostgreSQL database.",
        page_number=1,
        section_title="Architecture",
        meta_data={"document_name": "arch.pdf"}
    )

    vector_items = [{"chunk": mock_chunk, "score": 0.85}]
    graph_nodes = [{
        "id": str(uuid.uuid4()),
        "name": "PostgreSQL",
        "node_type": "SKILL",
        "description": "Relational database",
        "relevance_score": 0.90,
        "metadata": {"provenance": [{"chunk_id": str(chunk_id)}]}
    }]

    fused = fusion.fuse_results(vector_items=vector_items, graph_nodes=graph_nodes)
    assert len(fused) == 1 # Deduplicated and merged!
    item = fused[0]
    assert item.source_type == "hybrid"
    assert item.chunk_id == chunk_id
    assert item.entity_name == "PostgreSQL"
    assert item.score > 0.7

def test_conflict_detection():
    items = [
        HybridRetrievedItem(content="FastAPI is the primary backend framework.", source_type="document", score=0.9),
        HybridRetrievedItem(content="Legacy Flask endpoint is deprecated and replaced by FastAPI.", source_type="document", score=0.8)
    ]
    has_conflict, summary = HybridScoreFusion.detect_conflicts(items)
    assert has_conflict is True
    assert "deprecated" in summary

def test_hybrid_context_builder_budget_limits():
    builder = HybridContextBuilder(HybridFusionConfig(max_context_chars=300))
    items = [
        HybridRetrievedItem(
            content="Evidence snippet A " * 10,
            source_type="document",
            document_name="DocA.pdf",
            score=0.9
        ),
        HybridRetrievedItem(
            content="Evidence snippet B " * 10,
            source_type="document",
            document_name="DocB.pdf",
            score=0.8
        )
    ]
    context = builder.build_hybrid_context(items, graph_context="AegisAI -> USES -> Python")
    assert len(context) <= 400
    assert "=== DOCUMENT EVIDENCE ===" in context
    assert "=== KNOWLEDGE GRAPH TOPOLOGY ===" in context

@pytest.mark.asyncio
async def test_hybrid_rag_service_mock_pipeline(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    w1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    # Add a knowledge graph node
    node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=w1,
        name="PostgreSQL",
        node_type=NodeType.SKILL.value,
        description="Database engine"
    )
    db_session.add(node)
    db_session.commit()

    # Mock Retriever, Reranker, Citation, Generator
    mock_retriever = AsyncMock()
    mock_chunk = MagicMock(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="PostgreSQL stores structured tenant state.",
        page_number=1,
        section_title="DB",
        meta_data={"document_name": "db_spec.pdf"}
    )
    mock_retriever.retrieve.return_value = [{"chunk": mock_chunk, "score": 0.9}]

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [{"chunk": mock_chunk, "score": 0.95}]

    mock_citation = MagicMock()
    mock_citation.extract_citations.return_value = []

    mock_generator = AsyncMock()
    mock_generator.generate.return_value = "AegisAI uses PostgreSQL for relational data storage."

    service = HybridRAGService(
        db=db_session,
        redis_client=None,
        retriever=mock_retriever,
        reranker=mock_reranker,
        citation_system=mock_citation,
        generator=mock_generator
    )

    res = await service.query_hybrid(
        query="What database does the platform use?",
        user_id=u1,
        workspace_id=w1
    )

    assert isinstance(res, HybridRAGResult)
    assert "PostgreSQL" in res.answer
    assert res.confidence >= 0.8
    assert len(res.retrieved_chunks) >= 1

def test_tenant_isolation_in_hybrid_rag(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    w1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    w2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    # Node in workspace 1
    node1 = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=w1,
        name="Tenant1SecretProject",
        node_type=NodeType.PROJECT.value
    )
    db_session.add(node1)
    db_session.commit()

    service = HybridRAGFactory.get_hybrid_rag_service(db_session, None)
    
    # Workspace 2 queries for Workspace 1's project -> must find 0 nodes
    found = service.kg_service.search_nodes(user_id=u2, workspace_id=w2, query="Tenant1SecretProject")
    assert len(found) == 0
