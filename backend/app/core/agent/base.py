import abc
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.core.agent.state import AgentState

class AgentResult(BaseModel):
    """
    Standardized result data returned by individual agents.
    """
    agent_name: str
    status: str
    output: str
    confidence: float
    execution_time: float
    token_usage: Dict[str, int]
    errors: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ExecutionContext(BaseModel):
    """
    Configuration credentials and permission parameters passed to the graph runtime.
    """
    request_id: str
    user_id: str
    workspace_id: str
    conversation_id: str
    permissions: List[str] = []
    model: str
    provider: str
    configuration: Dict[str, Any] = {}

class BaseAgent(abc.ABC):
    """
    Common contract every specialized AegisAI agent must inherit.
    """
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass

    @abc.abstractmethod
    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        pass

    @abc.abstractmethod
    def validate_input(self, state: AgentState) -> bool:
        pass

    @abc.abstractmethod
    def validate_output(self, result: AgentResult) -> bool:
        pass

    @abc.abstractmethod
    def health_check(self) -> bool:
        pass
