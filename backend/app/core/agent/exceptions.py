class AgentEngineException(Exception):
    """
    Base exception class for all Multi-Agent engine exceptions.
    """
    def __init__(self, message: str, code: str = "AGENT_ENGINE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class AgentTimeout(AgentEngineException):
    def __init__(self, message: str = "Agent execution timed out."):
        super().__init__(message, code="AGENT_TIMEOUT")

class AgentExecutionError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="AGENT_EXECUTION_ERROR")

class AgentValidationError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="AGENT_VALIDATION_ERROR")

class GraphExecutionError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="GRAPH_EXECUTION_ERROR")

class AgentUnavailable(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="AGENT_UNAVAILABLE")

class InvalidStateTransition(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="INVALID_STATE_TRANSITION")

class ResearchProviderUnavailable(AgentEngineException):
    def __init__(self, message: str = "Research provider is unavailable."):
        super().__init__(message, code="RESEARCH_PROVIDER_UNAVAILABLE")

class ResearchTimeout(AgentEngineException):
    def __init__(self, message: str = "Research query execution timed out."):
        super().__init__(message, code="RESEARCH_TIMEOUT")

class NoResultsFound(AgentEngineException):
    def __init__(self, message: str = "No search results returned by provider."):
        super().__init__(message, code="NO_RESULTS_FOUND")

class InvalidResearchRequest(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="INVALID_RESEARCH_REQUEST")

class SourceRetrievalError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="SOURCE_RETRIEVAL_ERROR")

class InvalidResearchResult(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="INVALID_RESEARCH_RESULT")

class MemoryProviderUnavailable(AgentEngineException):
    def __init__(self, message: str = "Memory provider is unavailable."):
        super().__init__(message, code="MEMORY_PROVIDER_UNAVAILABLE")

class MemoryQueryError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="MEMORY_QUERY_ERROR")

class MemoryNotFound(AgentEngineException):
    def __init__(self, message: str = "Target memory record was not found."):
        super().__init__(message, code="MEMORY_NOT_FOUND")

class InvalidMemoryRecord(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="INVALID_MEMORY_RECORD")

class MemoryPermissionError(AgentEngineException):
    def __init__(self, message: str = "Permission denied for this memory record."):
        super().__init__(message, code="MEMORY_PERMISSION_ERROR")

class MemoryLimitExceeded(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="MEMORY_LIMIT_EXCEEDED")

class SensitiveMemoryRejected(AgentEngineException):
    def __init__(self, message: str = "Memory contains restricted credentials/secrets and was rejected."):
        super().__init__(message, code="SENSITIVE_MEMORY_REJECTED")

class ToolNotFound(AgentEngineException):
    def __init__(self, message: str = "The requested tool was not found."):
        super().__init__(message, code="TOOL_NOT_FOUND")

class ToolDisabled(AgentEngineException):
    def __init__(self, message: str = "The tool is currently disabled."):
        super().__init__(message, code="TOOL_DISABLED")

class ToolPermissionDenied(AgentEngineException):
    def __init__(self, message: str = "Access denied for this tool."):
        super().__init__(message, code="TOOL_PERMISSION_DENIED")

class ToolArgumentValidationError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="TOOL_ARGUMENT_VALIDATION_ERROR")

class ToolExecutionError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="TOOL_EXECUTION_ERROR")

class ToolTimeout(AgentEngineException):
    def __init__(self, message: str = "Tool execution timed out."):
        super().__init__(message, code="TOOL_TIMEOUT")

class ToolConfirmationRequired(AgentEngineException):
    def __init__(self, message: str = "Human confirmation is required before execution."):
        super().__init__(message, code="TOOL_CONFIRMATION_REQUIRED")

class ToolConfirmationInvalid(AgentEngineException):
    def __init__(self, message: str = "Supplied confirmation token is invalid or expired."):
        super().__init__(message, code="TOOL_CONFIRMATION_INVALID")

class ToolAlreadyExecuted(AgentEngineException):
    def __init__(self, message: str = "Tool execution request has already been executed (Idempotency conflict)."):
        super().__init__(message, code="TOOL_ALREADY_EXECUTED")

class ToolRegistryError(AgentEngineException):
    def __init__(self, message: str):
        super().__init__(message, code="TOOL_REGISTRY_ERROR")



