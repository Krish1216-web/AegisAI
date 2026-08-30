import google.generativeai as genai
from typing import List
from app.core.embeddings.base import BaseEmbeddingProvider
from app.core.embeddings.exceptions import EmbeddingProviderException

class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        genai.configure(api_key=api_key)
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        try:
            res = genai.embed_content(model=self.model, content=text)
            return res['embedding']
        except Exception as e:
            raise EmbeddingProviderException(f"Gemini embedding failed: {str(e)}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            res = genai.embed_content(model=self.model, content=texts)
            return res['embedding']
        except Exception as e:
            raise EmbeddingProviderException(f"Gemini batch embedding failed: {str(e)}")
