from app.core.exceptions import AegisBaseException

class EmbeddingProviderException(AegisBaseException):
    """Base exception for embedding provider errors."""
    pass

class EmbeddingDimensionMismatch(EmbeddingProviderException):
    """Raised when generated embedding dimension does not match configured dimension."""
    pass
