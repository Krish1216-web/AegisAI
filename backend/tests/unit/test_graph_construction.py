import pytest
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.document import Document, DocumentChunk
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.graph_construction import GraphConstructionService

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
    org = Organization(id=org_id, name="Test Graph Org")
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

def create_sample_document(db, user_id, workspace_id, filename="architecture.pdf"):
    doc = Document(
        id=uuid.uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        filename=filename,
        original_filename=filename,
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1024,
        checksum=f"chk_{uuid.uuid4()}",
        storage_path=f"storage/{filename}",
        status="EMBEDDING",
        page_count=2
    )
    db.add(doc)
    db.commit()

    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=user_id,
        workspace_id=workspace_id,
        chunk_index=0,
        content="AegisAI Architecture Specification. Built with FastAPI and PostgreSQL.",
        content_hash=f"hash_{uuid.uuid4()}",
        character_count=65,
        token_count=12,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536,
        start_offset=0,
        end_offset=65,
        page_number=1,
        section_title="Architecture"
    )
    chunk2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=user_id,
        workspace_id=workspace_id,
        chunk_index=1,
        content="The user interface is powered by React and connects to ChromaDB vector memory.",
        content_hash=f"hash_{uuid.uuid4()}",
        character_count=78,
        token_count=14,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536,
        start_offset=66,
        end_offset=144,
        page_number=2,
        section_title="Frontend & Memory"
    )
    db.add_all([chunk1, chunk2])
    db.commit()

    return doc, [chunk1, chunk2]

def test_graph_construction_from_document(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    doc, chunks = create_sample_document(db_session, user_id, ws_id)

    construction_service = GraphConstructionService(db_session)
    result = construction_service.construct_graph_from_document(
        document_id=doc.id,
        user_id=user_id,
        workspace_id=ws_id
    )

    assert result["status"] == "completed"
    assert result["chunks_processed"] == 2
    assert result["entities_extracted"] >= 4

    entities = construction_service.get_document_entities(doc.id, user_id, ws_id)
    entity_names = [e.name for e in entities]
    assert "FastAPI" in entity_names
    assert "PostgreSQL" in entity_names
    assert "React" in entity_names
    assert "ChromaDB" in entity_names

    relationships = construction_service.get_document_relationships(doc.id, user_id, ws_id)
    assert len(relationships) >= 4

def test_graph_construction_idempotency(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    doc, chunks = create_sample_document(db_session, user_id, ws_id)

    construction_service = GraphConstructionService(db_session)

    # First run
    res1 = construction_service.construct_graph_from_document(doc.id, user_id, ws_id)
    nodes_count_1 = db_session.query(KnowledgeGraphNode).count()
    edges_count_1 = db_session.query(KnowledgeGraphEdge).count()

    # Second run on same document
    res2 = construction_service.construct_graph_from_document(doc.id, user_id, ws_id)
    nodes_count_2 = db_session.query(KnowledgeGraphNode).count()
    edges_count_2 = db_session.query(KnowledgeGraphEdge).count()

    # Must be 100% idempotent: zero duplicate nodes or duplicate edges
    assert nodes_count_1 == nodes_count_2
    assert edges_count_1 == edges_count_2

def test_rebuild_document_graph(db_session):
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    doc, chunks = create_sample_document(db_session, user_id, ws_id)

    construction_service = GraphConstructionService(db_session)
    construction_service.construct_graph_from_document(doc.id, user_id, ws_id)

    # Rebuild
    rebuild_res = construction_service.rebuild_document_graph(doc.id, user_id, ws_id)
    assert rebuild_res["status"] == "completed"

    entities = construction_service.get_document_entities(doc.id, user_id, ws_id)
    assert len(entities) >= 4

def test_graph_construction_tenant_isolation(db_session):
    user_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws_1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    doc_1, _ = create_sample_document(db_session, user_1, ws_1, "user1_doc.pdf")

    user_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ws_2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    construction_service = GraphConstructionService(db_session)

    # User 2 attempting to construct/access User 1's document must fail
    with pytest.raises(ValueError, match="not found in workspace"):
        construction_service.construct_graph_from_document(
            document_id=doc_1.id,
            user_id=user_2,
            workspace_id=ws_2
        )

    # User 2 retrieving User 1's entities returns empty
    u2_entities = construction_service.get_document_entities(doc_1.id, user_2, ws_2)
    assert len(u2_entities) == 0
