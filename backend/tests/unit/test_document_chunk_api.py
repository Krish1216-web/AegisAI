import pytest
import uuid
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.document import Document, DocumentChunk

# Setup SQLite in-memory database with StaticPool
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db")
def db_fixture():
    session = TestingSessionLocal()
    session.query(DocumentChunk).delete()
    session.query(Document).delete()
    session.query(WorkspaceMember).delete()
    session.query(Workspace).delete()
    session.query(User).delete()
    session.query(Role).delete()
    session.query(Organization).delete()
    session.commit()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(name="client")
def client_fixture(db):
    org = Organization(id=uuid.uuid4(), name="Chunking Corp")
    db.add(org)
    db.commit()
    
    role = Role(id=uuid.uuid4(), name="User")
    db.add(role)
    db.commit()
    
    # User A
    workspace_a_id = uuid.uuid4()
    user_a = User(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="user_a@aegis.ai",
        username="user_a",
        password_hash="hashed",
        role_id=role.id,
        settings={"default_workspace_id": str(workspace_a_id)},
        is_active=True
    )
    db.add(user_a)
    db.commit()
    
    workspace_a = Workspace(id=workspace_a_id, organization_id=org.id, name="Workspace A")
    db.add(workspace_a)
    db.commit()
    
    member_a = WorkspaceMember(workspace_id=workspace_a_id, user_id=user_a.id, role="owner")
    db.add(member_a)
    db.commit()

    # User B
    workspace_b_id = uuid.uuid4()
    user_b = User(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="user_b@aegis.ai",
        username="user_b",
        password_hash="hashed",
        role_id=role.id,
        settings={"default_workspace_id": str(workspace_b_id)},
        is_active=True
    )
    db.add(user_b)
    db.commit()
    
    workspace_b = Workspace(id=workspace_b_id, organization_id=org.id, name="Workspace B")
    db.add(workspace_b)
    db.commit()
    
    member_b = WorkspaceMember(workspace_id=workspace_b_id, user_id=user_b.id, role="owner")
    db.add(member_b)
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return user_a

    def override_get_workspace_member(workspace_id: uuid.UUID):
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_a.id
        ).first()
        return member

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_workspace_member] = override_get_workspace_member
    
    client = TestClient(app, base_url="http://localhost")
    client.user_a = user_a
    client.user_b = user_b
    client.workspace_a_id = workspace_a_id
    client.workspace_b_id = workspace_b_id
    
    yield client
    app.dependency_overrides.clear()

def test_api_list_chunks_and_details(client, db):
    # Setup document uploaded by User A
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=client.user_a.id,
        workspace_id=client.workspace_a_id,
        filename="report.pdf",
        original_filename="report.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=100,
        checksum="hash3",
        storage_path="some_path",
        status="READY"
    )
    db.add(doc)
    db.commit()

    chunk_id = uuid.uuid4()
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        user_id=client.user_a.id,
        workspace_id=client.workspace_a_id,
        chunk_index=0,
        content="This is the first segment.",
        content_hash="h1",
        token_count=6,
        character_count=26,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536
    )
    db.add(chunk)
    db.commit()

    # List Chunks
    response = client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "This is the first segment."
    # Assert vector embedding was omitted from list payload response!
    assert "embedding" not in data[0]

    # Get Single Chunk details
    detail_response = client.get(f"/api/v1/documents/{doc_id}/chunks/{chunk_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["id"] == str(chunk_id)
    assert detail_data["content"] == "This is the first segment."
    # Assert vector embedding was omitted from details payload response!
    assert "embedding" not in detail_data

def test_api_trigger_chunking_and_reindex(client, db):
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=client.user_a.id,
        workspace_id=client.workspace_a_id,
        filename="report.pdf",
        original_filename="report.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=100,
        checksum="hash3",
        storage_path="some_path",
        status="READY"
    )
    db.add(doc)
    db.commit()

    # Trigger chunk (queues background task)
    with patch("fastapi.BackgroundTasks.add_task") as mock_add:
        response = client.post(f"/api/v1/documents/{doc_id}/chunk")
        assert response.status_code == 202
        assert response.json()["status"] == "PROCESSING"
        assert mock_add.call_count == 1

    # Trigger reindex (queues background task)
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_reindex:
        response = client.post(f"/api/v1/documents/{doc_id}/reindex")
        assert response.status_code == 202
        assert response.json()["status"] == "PROCESSING"
        assert mock_add_reindex.call_count == 1

def test_api_chunk_tenant_isolation(client, db):
    # User B's document in Workspace B
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=client.user_b.id,
        workspace_id=client.workspace_b_id,
        filename="secret.pdf",
        original_filename="secret.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=100,
        checksum="hash4",
        storage_path="secret_path",
        status="READY"
    )
    db.add(doc)
    db.commit()

    # User A tries to view User B's document chunks
    response = client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert response.status_code == 403 or response.status_code == 404

    # User A tries to trigger chunking of User B's document
    chunk_response = client.post(f"/api/v1/documents/{doc_id}/chunk")
    assert chunk_response.status_code == 403 or chunk_response.status_code == 404
