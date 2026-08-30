import pytest
import uuid
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.document import Document
from app.services.document_storage import DocumentStorage

from sqlalchemy.pool import StaticPool

# Setup SQLite in-memory database with StaticPool to persist schemas across sessions
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
    # Clean table content between runs
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
    # Setup mock workspace and users
    org = Organization(id=uuid.uuid4(), name="API Corp")
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
        password_hash="hashed_pass",
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

    # User B (Tenant isolation checks)
    workspace_b_id = uuid.uuid4()
    user_b = User(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="user_b@aegis.ai",
        username="user_b",
        password_hash="hashed_pass",
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

    # Dependency overrides setup
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
    
    # Save test context properties
    client = TestClient(app, base_url="http://localhost")
    client.user_a = user_a
    client.user_b = user_b
    client.workspace_a_id = workspace_a_id
    client.workspace_b_id = workspace_b_id
    
    yield client
    
    # Tear down overrides
    app.dependency_overrides.clear()

def test_upload_valid_document(client, db):
    file_content = b"%PDF-1.5\n/Type /Pages /Count 1\n"
    files = {"file": ("report.pdf", file_content, "application/pdf")}
    
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "report.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_size"] == len(file_content)
    assert data["status"] == "UPLOADED"
    
    # Verify DB state
    db_doc = db.query(Document).filter(Document.id == uuid.UUID(data["document_id"])).first()
    assert db_doc is not None
    assert db_doc.user_id == client.user_a.id
    assert db_doc.workspace_id == client.workspace_a_id
    assert db_doc.page_count == 1  # PDF parser should pick page count

def test_duplicate_upload_rejection(client):
    file_content = b"%PDF-1.5 duplicate file content"
    files = {"file": ("report.pdf", file_content, "application/pdf")}
    
    response1 = client.post("/api/v1/documents/upload", files=files)
    assert response1.status_code == 201
    
    # Re-upload same file content (same checksum) within same workspace + user context
    response2 = client.post("/api/v1/documents/upload", files=files)
    assert response2.status_code == 409
    assert "DUPLICATE_DOCUMENT" in response2.text

def test_list_documents(client):
    file_content = b"%PDF-1.5 listing file content"
    files = {"file": ("log.pdf", file_content, "application/pdf")}
    
    client.post("/api/v1/documents/upload", files=files)
    
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "log.pdf"

def test_get_document_details(client):
    file_content = b"%PDF-1.5 details file content"
    files = {"file": ("audit.pdf", file_content, "application/pdf")}
    
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_res.json()["document_id"]
    
    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == doc_id
    assert data["filename"] == "audit.pdf"
    assert "metadata" in data

def test_delete_document(client, db):
    file_content = b"%PDF-1.5 delete file content"
    files = {"file": ("trash.pdf", file_content, "application/pdf")}
    
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = uuid.UUID(upload_res.json()["document_id"])
    
    # Delete
    response = client.delete(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 204
    
    # Verify DB status changed to DELETED
    db_doc = db.query(Document).filter(Document.id == doc_id).first()
    assert db_doc.status == "DELETED"
    assert db_doc.storage_path == ""
    
    # Try downloading deleted document
    download_res = client.get(f"/api/v1/documents/{doc_id}/download")
    assert download_res.status_code == 404

def test_download_document(client):
    file_content = b"%PDF-1.5 download file content"
    files = {"file": ("download.pdf", file_content, "application/pdf")}
    
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_res.json()["document_id"]
    
    response = client.get(f"/api/v1/documents/{doc_id}/download")
    assert response.status_code == 200
    assert response.content == file_content
    assert "attachment; filename=\"download.pdf\"" in response.headers["Content-Disposition"]

def test_tenant_isolation_restrictions(client, db):
    # Setup a document uploaded by User B in Workspace B
    doc_b_id = uuid.uuid4()
    doc_b = Document(
        id=doc_b_id,
        user_id=client.user_b.id,
        workspace_id=client.workspace_b_id,
        filename="secret.pdf",
        original_filename="secret.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=100,
        checksum="some_hash",
        storage_path="workspaces/b/documents/b/file",
        status="UPLOADED"
    )
    db.add(doc_b)
    db.commit()

    # User A tries to view User B's document
    res_details = client.get(f"/api/v1/documents/{doc_b_id}")
    assert res_details.status_code == 403 or res_details.status_code == 404
    
    # User A tries to download User B's document
    res_download = client.get(f"/api/v1/documents/{doc_b_id}/download")
    assert res_download.status_code == 403 or res_download.status_code == 404
    
    # User A tries to delete User B's document
    res_delete = client.delete(f"/api/v1/documents/{doc_b_id}")
    assert res_delete.status_code == 403 or res_delete.status_code == 404
