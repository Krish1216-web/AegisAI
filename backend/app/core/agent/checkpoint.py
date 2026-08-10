import abc
from typing import Dict, Any, Optional
from app.core.agent.state import AgentState

class BaseCheckpointer(abc.ABC):
    """
    Abstract contract for agent graph execution checkpointers.
    """
    @abc.abstractmethod
    def save(self, execution_id: str, state: AgentState) -> None:
        pass

    @abc.abstractmethod
    def load(self, execution_id: str) -> Optional[AgentState]:
        pass

class InMemoryCheckpointer(BaseCheckpointer):
    """
    Default in-memory state checkpointer for local development.
    """
    def __init__(self):
        self._storage: Dict[str, AgentState] = {}

    def save(self, execution_id: str, state: AgentState) -> None:
        self._storage[execution_id] = state.copy()

    def load(self, execution_id: str) -> Optional[AgentState]:
        return self._storage.get(execution_id)
