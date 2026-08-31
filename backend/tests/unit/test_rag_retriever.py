import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.document import DocumentChunk
from app.core.rag.retriever import VectorRetriever, cosine_similarity

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(name="db")
def db_fixture():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.query(DocumentChunk).delete()
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_cosine_similarity_calculation():
    v1 = [1.0, 0.0]
    v2 = [1.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0]
    assert cosine_similarity(v1, v3) == 0.0

@pytest.mark.asyncio
async def test_vector_retriever_tenant_isolation_and_threshold(db):
    user_1 = uuid.uuid4()
    user_2 = uuid.uuid4()
    ws_1 = uuid.uuid4()
    
    chunk_user1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        user_id=user_1,
        workspace_id=ws_1,
        chunk_index=0,
        content="Deep learning context.",
        content_hash="h1",
        token_count=10,
        character_count=22,
        embedding=[1.0, 0.0, 0.0],
        embedding_model="m1",
        embedding_dimension=3
    )
    
    chunk_user2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        user_id=user_2,
        workspace_id=ws_1,
        chunk_index=0,
        content="Deep learning context.",
        content_hash="h2",
        token_count=10,
        character_count=22,
        embedding=[1.0, 0.0, 0.0],
        embedding_model="m1",
        embedding_dimension=3
    )
    
    chunk_low_sim = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        user_id=user_1,
        workspace_id=ws_1,
        chunk_index=1,
        content="Apples and bananas.",
        content_hash="h3",
        token_count=10,
        character_count=20,
        embedding=[0.0, 1.0, 0.0],
        embedding_model="m1",
        embedding_dimension=3
    )

    db.add_all([chunk_user1, chunk_user2, chunk_low_sim])
    db.commit()

    mock_ai = MagicMock()
    mock_ai.generate_embeddings = AsyncMock(return_value=[1.0, 0.0, 0.0])

    retriever = VectorRetriever(mock_ai)
    
    # Query for User 1
    results = await retriever.retrieve(
        db=db,
        query="semantic query",
        user_id=user_1,
        workspace_id=ws_1,
        limit=5,
        similarity_threshold=0.5
    )
    
    # Should only match chunk_user1. chunk_user2 is other tenant, chunk_low_sim is below threshold.
    assert len(results) == 1
    assert results[0]["chunk"].id == chunk_user1.id
    assert results[0]["score"] == 1.0
