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
