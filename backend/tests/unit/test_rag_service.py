import pytest
import uuid
import json
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.database.redis import get_redis
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.document import Document, DocumentChunk
from app.models.rag import RAGQuery
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)

# Setup mock user and workspace
MOCK_USER_ID = uuid.uuid4()
MOCK_WS_ID = uuid.uuid4()

def mock_get_current_user():
    role = Role(id=uuid.uuid4(), name="User")
    user = User(
        id=MOCK_USER_ID,
        email="test@aegis.ai",
        username="testuser",
        password_hash="hash",
        role_id=role.id,
        is_active=True,
        settings={"default_workspace_id": str(MOCK_WS_ID)}
    )
    return user

def mock_check_rate_limit():
    return None

@pytest.fixture(name="db")
def db_fixture():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.query(RAGQuery).delete()
    session.query(DocumentChunk).delete()
    session.query(Document).delete()
    session.query(WorkspaceMember).delete()
    session.query(Workspace).delete()
    session.query(User).delete()
    session.query(Role).delete()
    session.query(Organization).delete()
    session.commit()
    
    # Seed org and workspace
    org = Organization(id=uuid.uuid4(), name="Test Org")
    session.add(org)
    session.commit()
    
    ws = Workspace(id=MOCK_WS_ID, organization_id=org.id, name="Test WS")
    session.add(ws)
    session.commit()
    
    role = Role(id=uuid.uuid4(), name="User")
    session.add(role)
    session.commit()
    
    user = User(
        id=MOCK_USER_ID,
        email="test@aegis.ai",
        username="testuser",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    session.add(user)
    session.commit()
    
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=MOCK_WS_ID, user_id=MOCK_USER_ID, role="member")
    session.add(member)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="redis_client")
def redis_client_fixture():
    client = MagicMock()
    client.get.return_value = None
    return client

@pytest.fixture(name="client")
def client_fixture(db, redis_client):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: redis_client
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit
    try:
        yield TestClient(app, base_url="http://localhost")
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_rag_service_caching_and_execution(db, redis_client):
    from app.core.rag.factory import RAGFactory
    
    # Create test chunks
    doc = Document(
        id=uuid.uuid4(),
        user_id=MOCK_USER_ID,
        workspace_id=MOCK_WS_ID,
        filename="specs.pdf",
        original_filename="specs.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=100,
        checksum="mock_checksum_val",
        storage_path="/mock/storage/specs.pdf"
    )
    db.add(doc)
    db.commit()
    
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=MOCK_USER_ID,
        workspace_id=MOCK_WS_ID,
        chunk_index=0,
        content="Deep learning architectures are complex.",
        content_hash="h1",
        token_count=10,
        character_count=40,
        embedding=[0.1]*1536,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536
    )
    db.add(chunk)
    db.commit()

    # Stub embedding generation
    mock_ai = MagicMock()
    mock_ai.generate_embeddings = AsyncMock(return_value=[0.1]*1536)
    mock_ai.generate_chat = AsyncMock(return_value=MagicMock(content="Answer text [1]."))

    with patch("app.core.rag.factory.AIService", return_value=mock_ai):
         
        rag_service = RAGFactory.get_rag_service(db, redis_client)
        
        # Query 1 (Cache Miss)
        resp = await rag_service.query_rag(
            query="test query",
            user_id=MOCK_USER_ID,
            workspace_id=MOCK_WS_ID,
            limit=5,
            similarity_threshold=0.0
        )
        
        assert resp.answer == "Answer text [1]."
        assert len(resp.citations) == 1
        assert resp.citations[0].document_name == "specs.pdf"
        
        # Verify db log
        logs = db.query(RAGQuery).all()
        assert len(logs) == 1
        assert logs[0].query == "test query"
        assert logs[0].is_cached is False
        
        # Verify Redis caching write
        assert redis_client.setex.call_count == 1

def test_rag_api_endpoints_query_and_stream(client, db, redis_client):
    # Setup document chunks
    doc = Document(
        id=uuid.uuid4(),
        user_id=MOCK_USER_ID,
        workspace_id=MOCK_WS_ID,
        filename="specs.pdf",
        original_filename="specs.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=100,
        checksum="mock_checksum_val",
        storage_path="/mock/storage/specs.pdf"
    )
    db.add(doc)
    db.commit()
    
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=MOCK_USER_ID,
        workspace_id=MOCK_WS_ID,
        chunk_index=0,
        content="Deep learning architectures are complex.",
        content_hash="h1",
        token_count=10,
        character_count=40,
        embedding=[0.1]*1536,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536
    )
    db.add(chunk)
    db.commit()

    mock_ai = MagicMock()
    mock_ai.generate_embeddings = AsyncMock(return_value=[0.1]*1536)
    mock_ai.generate_chat = AsyncMock(return_value=MagicMock(content="Generated answer [1]."))
    
    async def mock_stream_chat(*args, **kwargs):
        yield "Generated "
        yield "answer "
        yield "[1]."

    mock_ai.stream_chat = mock_stream_chat

    with patch("app.core.rag.factory.AIService", return_value=mock_ai), \
         patch("app.api.v1.endpoints.rag.AIService", return_value=mock_ai):
         
        # Test Query API
        response = client.post(
            "/api/v1/rag/query",
            json={
                "query": "what is complexity?",
                "limit": 5,
                "similarity_threshold": 0.0
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Generated answer [1]."
        assert len(data["citations"]) == 1
        assert data["citations"][0]["document_name"] == "specs.pdf"
        
        # Test Stream API (SSE)
        stream_response = client.get(
            "/api/v1/rag/stream",
            params={
                "query": "what is complexity?",
                "limit": 5,
                "similarity_threshold": 0.0
            }
        )
        assert stream_response.status_code == 200
        assert "text/event-stream" in stream_response.headers["content-type"]
        
        # Verify tokens streamed and metadata present in stream
        content = stream_response.text
        assert "data: Generated" in content
        assert "data: answer" in content
        assert "data: [METADATA]" in content
        assert "data: [DONE]" in content
