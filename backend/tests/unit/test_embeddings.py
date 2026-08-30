import pytest
from unittest.mock import MagicMock, patch

from app.core.embeddings.mock import MockEmbeddingProvider
from app.core.embeddings.factory import EmbeddingProviderFactory
from app.core.embeddings.exceptions import EmbeddingDimensionMismatch
from app.core.config import settings

def test_mock_embedding_provider():
    prov = MockEmbeddingProvider(dimension=1536)
    vec = prov.embed_text("test")
    assert len(vec) == 1536
    assert all(f == 0.1 for f in vec)

    batch_vecs = prov.embed_batch(["one", "two"])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 1536
    assert len(batch_vecs[1]) == 1536

def test_embedding_factory():
    # Force settings mock
    with patch.object(settings, "EMBEDDING_PROVIDER", "mock"):
        with patch.object(settings, "EMBEDDING_DIMENSION", 512):
            provider = EmbeddingProviderFactory.get_provider()
            assert isinstance(provider, MockEmbeddingProvider)
            assert provider.dimension == 512
            assert len(provider.embed_text("x")) == 512
