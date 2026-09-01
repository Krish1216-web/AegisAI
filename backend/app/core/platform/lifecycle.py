import enum
import datetime
from typing import Dict, Any, Optional, List, Set
from pydantic import BaseModel, Field

class LifecycleState(str, enum.Enum):
    REQUESTED = "requested"
    VALIDATING = "validating"
    PLANNED = "planned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    
    # Terminal / Intermediary States
    WAITING = "waiting"
    DENIED = "denied"
    FAILED = "failed"
    CANCELLED = "cancelled"

class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is attempted."""
    pass

class LifecycleEvent(BaseModel):
    """Immutable audit record of a state transition."""
    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Directed Transition Graph
ALLOWED_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    LifecycleState.REQUESTED: {
        LifecycleState.VALIDATING,
        LifecycleState.DENIED,
        LifecycleState.CANCELLED,
        LifecycleState.FAILED
    },
    LifecycleState.VALIDATING: {
        LifecycleState.PLANNED,
        LifecycleState.EXECUTING,
        LifecycleState.DENIED,
        LifecycleState.FAILED,
        LifecycleState.CANCELLED
    },
    LifecycleState.PLANNED: {
        LifecycleState.EXECUTING,
        LifecycleState.WAITING,
        LifecycleState.DENIED,
        LifecycleState.CANCELLED,
        LifecycleState.FAILED
    },
    LifecycleState.EXECUTING: {
        LifecycleState.VERIFYING,
        LifecycleState.WAITING,
        LifecycleState.COMPLETED,
        LifecycleState.FAILED,
        LifecycleState.CANCELLED
    },
    LifecycleState.WAITING: {
        LifecycleState.EXECUTING,
        LifecycleState.DENIED,
        LifecycleState.CANCELLED,
        LifecycleState.FAILED
    },
    LifecycleState.VERIFYING: {
        LifecycleState.COMPLETED,
        LifecycleState.EXECUTING, # Re-planning/retry
        LifecycleState.FAILED,
        LifecycleState.CANCELLED
    },
    # Terminal States (no outgoing transitions allowed)
    LifecycleState.COMPLETED: set(),
    LifecycleState.FAILED: set(),
    LifecycleState.CANCELLED: set(),
    LifecycleState.DENIED: set(),
}

class LifecycleStateMachine:
    """
    Deterministic State Machine for Phase 8 platform requests and executions.
    """
    def __init__(self, initial_state: LifecycleState = LifecycleState.REQUESTED):
        self._current_state = initial_state
        self._history: List[LifecycleEvent] = []

    @property
    def current_state(self) -> LifecycleState:
        return self._current_state

    @property
    def history(self) -> List[LifecycleEvent]:
        return list(self._history)

    def is_terminal(self) -> bool:
        return self._current_state in {
            LifecycleState.COMPLETED,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.DENIED
        }

    def transition_to(self, new_state: LifecycleState, reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> LifecycleState:
        """
        Validates and applies a deterministic state transition.
        """
        allowed = ALLOWED_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal state transition from '{self._current_state.value}' to '{new_state.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )

        event = LifecycleEvent(
            from_state=self._current_state,
            to_state=new_state,
            reason=reason,
            metadata=metadata or {}
        )
        self._history.append(event)
        self._current_state = new_state
        return self._current_state
