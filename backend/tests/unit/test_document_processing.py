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
from app.models.document import Document
from app.services.document_processing import DocumentProcessingService

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
    org = Organization(id=uuid.uuid4(), name="Proc Corp")
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

def test_document_processing_service_success(client, db):
    doc_id = uuid.uuid4()
    workspace_id = client.workspace_a_id
    user_id = client.user_a.id
    
    doc = Document(
        id=doc_id,
        user_id=user_id,
        workspace_id=workspace_id,
        filename="test.txt",
        original_filename="test.txt",
        mime_type="text/plain",
        file_extension=".txt",
        file_size=20,
        checksum="hash1",
        storage_path="workspaces/x/documents/y/file",
        status="UPLOADED"
    )
    db.add(doc)
    db.commit()

    # Mock storage and extractor factory
    mock_storage = MagicMock()
    mock_storage.get_file.return_value = b"Hello, AegisAI Document Normalizer!"
    
    with patch("app.services.document_processing.DocumentStorage", return_value=mock_storage):
        DocumentProcessingService.process_document(db, doc_id)
        
    db.refresh(doc)
    assert doc.status == "READY"
    assert doc.extracted_text_length == len("Hello, AegisAI Document Normalizer!")
    assert doc.meta_data["word_count"] == 4
    assert doc.meta_data["character_count"] == len("Hello, AegisAI Document Normalizer!")

def test_document_processing_service_failure(client, db):
    doc_id = uuid.uuid4()
    workspace_id = client.workspace_a_id
    user_id = client.user_a.id
    
    doc = Document(
        id=doc_id,
        user_id=user_id,
        workspace_id=workspace_id,
        filename="bad.pdf",
        original_filename="bad.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=20,
        checksum="hash2",
        storage_path="workspaces/x/documents/y/file",
        status="UPLOADED"
    )
    db.add(doc)
    db.commit()

    # Trigger failure by forcing storage to raise exception
    with patch("app.services.document_processing.DocumentStorage") as mock_class:
        mock_instance = mock_class.return_value
        mock_instance.get_file.side_effect = Exception("Read file corrupted db credentials password")
        
        DocumentProcessingService.process_document(db, doc_id)

    db.refresh(doc)
    assert doc.status == "FAILED"
    # Verify error string was sanitized to hide database secrets/creds
    assert "parser or system error" in doc.processing_error
    assert "password" not in doc.processing_error

def test_api_queue_process_and_status(client, db):
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
        status="UPLOADED"
    )
    db.add(doc)
    db.commit()

    # Process Document (queues background task)
    def mock_add_task(func, *args, **kwargs):
        session = args[0]
        did = args[1]
        d = session.query(Document).filter(Document.id == did).first()
        d.status = "PROCESSING"
        session.commit()

    with patch("fastapi.BackgroundTasks.add_task", side_effect=mock_add_task):
        response = client.post(f"/api/v1/documents/{doc_id}/process")
        assert response.status_code == 202
        data = response.json()
        assert data["document_id"] == str(doc_id)
        assert data["status"] == "PROCESSING"

    # Status Check
    status_response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["document_id"] == str(doc_id)
    assert status_data["status"] == "PROCESSING"

def test_api_process_conflict(client, db):
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
        status="PROCESSING"
    )
    db.add(doc)
    db.commit()

    # Post process should conflict if currently in PROCESSING status
    response = client.post(f"/api/v1/documents/{doc_id}/process")
    assert response.status_code == 409
    assert "currently being processed" in response.json()["detail"]

def test_api_process_tenant_isolation(client, db):
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
        status="UPLOADED"
    )
    db.add(doc)
    db.commit()

    # User A tries to process User B's document
    response = client.post(f"/api/v1/documents/{doc_id}/process")
    assert response.status_code == 403 or response.status_code == 404

    # User A tries to check status of User B's document
    status_response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert status_response.status_code == 403 or status_response.status_code == 404
