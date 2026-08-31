from app.core.config import settings
from app.core.embeddings.openai import OpenAIEmbeddingProvider
from app.core.embeddings.gemini import GeminiEmbeddingProvider
from app.core.embeddings.mock import MockEmbeddingProvider
from app.core.embeddings.base import BaseEmbeddingProvider
from app.core.ai.exceptions import InvalidAPIKeyException

class EmbeddingProviderFactory:
    @staticmethod
    def get_provider() -> BaseEmbeddingProvider:
        """
        Resolves the configured BaseEmbeddingProvider.
        Falls back to MockEmbeddingProvider in dev/test settings when API keys are missing.
        """
        prov = settings.EMBEDDING_PROVIDER.lower()
        dim = settings.EMBEDDING_DIMENSION
        
        if prov == "openai":
            key = getattr(settings, "OPENAI_API_KEY", None)
            if not key or key == "":
                if settings.ENVIRONMENT != "prod":
                    return MockEmbeddingProvider(dimension=dim)
                raise InvalidAPIKeyException("OpenAI API key is not configured in settings.")
            return OpenAIEmbeddingProvider(api_key=key, model=settings.EMBEDDING_MODEL)
            
        elif prov == "gemini":
            key = getattr(settings, "GEMINI_API_KEY", None)
            if not key or key == "":
                if settings.ENVIRONMENT != "prod":
                    return MockEmbeddingProvider(dimension=dim)
                raise InvalidAPIKeyException("Google Gemini API key is not configured in settings.")
            return GeminiEmbeddingProvider(api_key=key, model=settings.EMBEDDING_MODEL)
            
        elif prov == "mock":
            return MockEmbeddingProvider(dimension=dim)
            
        return MockEmbeddingProvider(dimension=dim)
