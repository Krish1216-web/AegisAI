import pytest
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.entity_extraction.relationship_extractor import RelationshipExtractor, RelationshipValidationResult
from app.services.entity_extraction.models import ExtractedRelationship

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

    org = Organization(id=uuid.uuid4(), name="Relationship Test Org")
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

def test_valid_relationship_persistence(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    extractor = RelationshipExtractor(db_session)

    src = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="AegisAI", node_type="PROJECT")
    tgt = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="FastAPI", node_type="SKILL")
    db_session.add_all([src, tgt])
    db_session.commit()

    rel = ExtractedRelationship(
        source_entity_name="AegisAI",
        target_entity_name="FastAPI",
        relationship_type=RelationshipType.USES.value,
        confidence=0.92,
        source_text="AegisAI backend uses FastAPI for API routing.",
        document_id=uuid.uuid4(),
        chunk_id=uuid.uuid4()
    )

    edge = extractor.persist_relationship(u1, ws1, src, tgt, rel)
    assert edge is not None
    assert edge.source_node_id == src.id
    assert edge.target_node_id == tgt.id
    assert edge.relationship_type == RelationshipType.USES.value
    assert edge.confidence == 0.92
    assert edge.meta_data.get("source_text") == rel.source_text

def test_invalid_relationship_rejection(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    extractor = RelationshipExtractor(db_session)

    src = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="SelfNode", node_type="PROJECT")
    db_session.add(src)
    db_session.commit()

    # 1. Self-loop rejection
    rel_loop = ExtractedRelationship(
        source_entity_name="SelfNode",
        target_entity_name="SelfNode",
        relationship_type=RelationshipType.USES.value,
        confidence=0.9
    )
    edge_loop = extractor.persist_relationship(u1, ws1, src, src, rel_loop)
    assert edge_loop is None

    # 2. Invalid relationship type validation
    tgt = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="TgtNode", node_type="PROJECT")
    db_session.add(tgt)
    db_session.commit()

    # Pydantic validation rejects invalid relationship type
    with pytest.raises(Exception):
        ExtractedRelationship(
            source_entity_name="SelfNode",
            target_entity_name="TgtNode",
            relationship_type="MAGIC_TELEPORTS_TO",
            confidence=0.9
        )

def test_duplicate_edge_prevention_and_confidence_update(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    extractor = RelationshipExtractor(db_session)

    src = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="AegisAI", node_type="PROJECT")
    tgt = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="PostgreSQL", node_type="SKILL")
    db_session.add_all([src, tgt])
    db_session.commit()

    # 1. First insert
    rel1 = ExtractedRelationship(
        source_entity_name="AegisAI",
        target_entity_name="PostgreSQL",
        relationship_type=RelationshipType.USES.value,
        confidence=0.80,
        source_text="AegisAI uses PostgreSQL."
    )
    edge1 = extractor.persist_relationship(u1, ws1, src, tgt, rel1)
    assert edge1.confidence == 0.80

    # 2. Second insert with higher confidence
    rel2 = ExtractedRelationship(
        source_entity_name="AegisAI",
        target_entity_name="PostgreSQL",
        relationship_type=RelationshipType.USES.value,
        confidence=0.95,
        source_text="AegisAI is built strictly on PostgreSQL pgvector database."
    )
    edge2 = extractor.persist_relationship(u1, ws1, src, tgt, rel2)

    assert edge2.id == edge1.id
    assert edge2.confidence == 0.95
    total_edges = db_session.query(KnowledgeGraphEdge).filter(KnowledgeGraphEdge.workspace_id == ws1).count()
    assert total_edges == 1

def test_cross_tenant_relationship_rejection(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ws2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    extractor = RelationshipExtractor(db_session)

    src_ws1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="WS1Node", node_type="PROJECT")
    tgt_ws2 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u2, workspace_id=ws2, name="WS2Node", node_type="PROJECT")
    db_session.add_all([src_ws1, tgt_ws2])
    db_session.commit()

    rel = ExtractedRelationship(
        source_entity_name="WS1Node",
        target_entity_name="WS2Node",
        relationship_type=RelationshipType.REFERENCES.value,
        confidence=0.9
    )

    # Attempting to connect nodes across workspace boundaries must be rejected
    edge = extractor.persist_relationship(u1, ws1, src_ws1, tgt_ws2, rel)
    assert edge is None
