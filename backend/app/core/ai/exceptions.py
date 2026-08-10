class AIProviderException(Exception):
    """
    Base exception for all AI provider errors.
    """
    def __init__(self, message: str, code: str = "PROVIDER_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class InvalidAPIKeyException(AIProviderException):
    def __init__(self, message: str = "Invalid API Key provided for LLM endpoint."):
        super().__init__(message, code="INVALID_API_KEY", status_code=401)

class RateLimitException(AIProviderException):
    def __init__(self, message: str = "Rate limit exceeded for provider endpoint."):
        super().__init__(message, code="RATE_LIMIT_EXCEEDED", status_code=429)

class ProviderTimeoutException(AIProviderException):
    def __init__(self, message: str = "Request to AI provider timed out."):
        super().__init__(message, code="PROVIDER_TIMEOUT", status_code=504)

class ContextLengthExceededException(AIProviderException):
    def __init__(self, message: str = "Context length limit exceeded for target model."):
        super().__init__(message, code="CONTEXT_LENGTH_EXCEEDED", status_code=400)

class ModelNotFoundException(AIProviderException):
    def __init__(self, message: str = "Target LLM model was not found or is inactive."):
        super().__init__(message, code="MODEL_NOT_FOUND", status_code=404)

class InvalidRequestException(AIProviderException):
    def __init__(self, message: str = "Invalid parameters provided to the LLM model."):
        super().__init__(message, code="INVALID_REQUEST", status_code=400)
