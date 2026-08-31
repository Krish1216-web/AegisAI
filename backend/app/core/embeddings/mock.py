from typing import List
from app.core.embeddings.base import BaseEmbeddingProvider

class MockEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        # Return static mock floats matching configured dimension
        return [0.1] * self.dimension

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Return static list of mock floats
        return [[0.1] * self.dimension for _ in texts]
