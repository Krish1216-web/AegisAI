import abc
from typing import Dict, Any, Optional
from app.core.agent.exceptions import MemoryPermissionError

# We use forward references or Any for AgentState to avoid import cycles
AgentState = Any

class BaseCheckpointer(abc.ABC):
    """
    Abstract contract for agent graph execution checkpointers.
    """
    @abc.abstractmethod
    def save(self, execution_id: str, state: AgentState) -> None:
        pass

    @abc.abstractmethod
    def load(self, execution_id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Optional[AgentState]:
        pass

    @abc.abstractmethod
    def delete(self, execution_id: str) -> None:
        pass

    @abc.abstractmethod
    def exists(self, execution_id: str) -> bool:
        pass

class InMemoryCheckpointer(BaseCheckpointer):
    """
    Default in-memory state checkpointer for local development.
    """
    def __init__(self):
        self._storage: Dict[str, AgentState] = {}

    def save(self, execution_id: str, state: AgentState) -> None:
        self._storage[execution_id] = state.copy()

    def load(self, execution_id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Optional[AgentState]:
        state = self._storage.get(execution_id)
        if not state:
            return None
        if user_id and state.get("user_id") != user_id:
            raise MemoryPermissionError("Permission denied: Checkpoint belongs to another user")
        if workspace_id and state.get("workspace_id") != workspace_id:
            raise MemoryPermissionError("Permission denied: Checkpoint belongs to another workspace")
        return state

    def delete(self, execution_id: str) -> None:
        if execution_id in self._storage:
            del self._storage[execution_id]

    def exists(self, execution_id: str) -> bool:
        return execution_id in self._storage
