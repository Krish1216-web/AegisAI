import openai
from typing import List
from app.core.embeddings.base import BaseEmbeddingProvider
from app.core.embeddings.exceptions import EmbeddingProviderException

class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        try:
            res = self.client.embeddings.create(input=text, model=self.model)
            return res.data[0].embedding
        except Exception as e:
            raise EmbeddingProviderException(f"OpenAI embedding failed: {str(e)}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            res = self.client.embeddings.create(input=texts, model=self.model)
            # Sort to preserve request order index mapping
            sorted_data = sorted(res.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            raise EmbeddingProviderException(f"OpenAI batch embedding failed: {str(e)}")
