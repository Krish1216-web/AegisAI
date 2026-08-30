import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.core.rag.hybrid import (
    HybridRetrievedItem,
    HybridFusionConfig,
    HybridRAGResult,
    QueryEntityExtractor,
    HybridScoreFusion,
    HybridContextBuilder,
    HybridRAGService
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

    org = Organization(id=uuid.uuid4(), name="Graph RAG Test Org")
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

@pytest.mark.asyncio
async def test_graph_rag_enhancement_with_resolved_entities_and_edges(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    # 1. Create Graph Nodes and Edge
    src = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="AegisAI", node_type="PROJECT", description="AI agent platform")
    tgt = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="PostgreSQL", node_type="SKILL", description="Database engine")
    db_session.add_all([src, tgt])
    db_session.commit()

    edge = KnowledgeGraphEdge(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        source_node_id=src.id,
        target_node_id=tgt.id,
        relationship_type=RelationshipType.USES.value,
        confidence=0.95
    )
    db_session.add(edge)
    db_session.commit()

    # 2. Setup Mocks
    mock_retriever = AsyncMock()
    chunk_id = uuid.uuid4()
    mock_chunk = MagicMock(
        id=chunk_id,
        document_id=uuid.uuid4(),
        content="AegisAI utilizes PostgreSQL database for persistence.",
        page_number=1,
        section_title="DB Architecture",
        meta_data={"document_name": "architecture.pdf"}
    )
    mock_retriever.retrieve.return_value = [{"chunk": mock_chunk, "score": 0.88}]

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [{"chunk": mock_chunk, "score": 0.90}]

    mock_citation = MagicMock()
    mock_citation.extract_citations.return_value = []

    mock_generator = AsyncMock()
    mock_generator.generate.return_value = "AegisAI is connected to PostgreSQL via the USES relationship."

    service = HybridRAGService(
        db=db_session,
        redis_client=None,
        retriever=mock_retriever,
        reranker=mock_reranker,
        citation_system=mock_citation,
        generator=mock_generator
    )

    # 3. Query Hybrid RAG
    result = await service.query_hybrid(
        query="What is the relationship between AegisAI and PostgreSQL?",
        user_id=u1,
        workspace_id=ws1
    )

    assert isinstance(result, HybridRAGResult)
    assert len(result.graph_entities) >= 2
    assert len(result.graph_relationships) >= 1
    assert result.graph_relationships[0]["relationship_type"] == RelationshipType.USES.value
    assert "=== DOCUMENT EVIDENCE ===" in result.combined_context
    assert result.confidence >= 0.85

@pytest.mark.asyncio
async def test_graph_rag_no_evidence_fallback(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    # Mocks return empty evidence
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = []
    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = []
    mock_citation = MagicMock()
    mock_generator = AsyncMock()

    service = HybridRAGService(
        db=db_session,
        redis_client=None,
        retriever=mock_retriever,
        reranker=mock_reranker,
        citation_system=mock_citation,
        generator=mock_generator
    )

    result = await service.query_hybrid(
        query="Tell me about completely nonexistent secret project X",
        user_id=u1,
        workspace_id=ws1
    )

    assert "couldn't find" in result.answer.lower()
    assert result.confidence <= 0.2
    assert len(result.retrieved_chunks) == 0
