import pytest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.document import DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.core.embeddings.exceptions import EmbeddingDimensionMismatch
from app.core.config import settings

# In-memory database setup
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

def test_embedding_service_store_and_idempotency(db):
    doc_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    # Create two chunks. Chunk 1 and Chunk 2 have identical content hashes!
    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        workspace_id=workspace_id,
        chunk_index=0,
        content="Same content text.",
        content_hash="hash_same",
        token_count=10,
        character_count=18,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536
    )
    chunk2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        workspace_id=workspace_id,
        chunk_index=1,
        content="Same content text.",
        content_hash="hash_same",
        token_count=10,
        character_count=18,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536
    )
    db.add(chunk1)
    db.add(chunk2)
    db.commit()

    # Stub the mock provider to track how many times it was called
    mock_provider = MagicMock()
    mock_provider.embed_batch.return_value = [[0.5] * 1536]

    with patch("app.services.embedding_service.EmbeddingProviderFactory.get_provider", return_value=mock_provider):
        EmbeddingService.generate_and_store_embeddings(db, [chunk1, chunk2])

    db.refresh(chunk1)
    db.refresh(chunk2)

    # Chunk 1 should have got it from provider
    assert chunk1.embedding is not None
    assert chunk1.embedding[0] == 0.5
    # Chunk 2 should have REUSED it from the database instead of invoking mock_provider again!
    assert chunk2.embedding is not None
    assert chunk2.embedding[0] == 0.5
    
    # embed_batch should only have been called ONCE for the unique hash content!
    assert mock_provider.embed_batch.call_count == 1

def test_embedding_service_model_change_regeneration(db):
    doc_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    # Chunk with existing embedding from an old model
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        workspace_id=workspace_id,
        chunk_index=0,
        content="Some text content.",
        content_hash="hash_a",
        token_count=10,
        character_count=18,
        embedding=[0.9] * 1536,
        embedding_model="old-model-name",
        embedding_dimension=1536
    )
    db.add(chunk)
    db.commit()

    mock_provider = MagicMock()
    # Return different embedding for new model
    mock_provider.embed_batch.return_value = [[0.2] * 1536]

    with patch("app.services.embedding_service.EmbeddingProviderFactory.get_provider", return_value=mock_provider):
        with patch.object(settings, "EMBEDDING_MODEL", "text-embedding-3-small"):
            EmbeddingService.generate_and_store_embeddings(db, [chunk])

    db.refresh(chunk)
    # The embedding should be regenerated using the new model!
    assert chunk.embedding_model == "text-embedding-3-small"
    assert chunk.embedding[0] == 0.2
    assert mock_provider.embed_batch.call_count == 1

def test_embedding_service_retry_and_failure():
    mock_provider = MagicMock()
    mock_provider.embed_batch.side_effect = Exception("Rate limit hit 429")

    # Verify that the helper retries 3 times and throws the exception eventually
    with patch("app.services.embedding_service.time.sleep") as mock_sleep:
        with pytest.raises(Exception) as exc_info:
            EmbeddingService._embed_with_retry(mock_provider, ["sample text"])
        assert "Embedding generation failed" in str(exc_info.value)
        # Should have called embed_batch 3 times and sleep 2 times
        assert mock_provider.embed_batch.call_count == 3
        assert mock_sleep.call_count == 2
