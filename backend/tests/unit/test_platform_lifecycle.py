import pytest
from app.core.platform.lifecycle import (
    LifecycleState,
    LifecycleStateMachine,
    InvalidStateTransitionError
)

def test_valid_lifecycle_transitions():
    sm = LifecycleStateMachine(initial_state=LifecycleState.REQUESTED)
    assert sm.current_state == LifecycleState.REQUESTED
    assert not sm.is_terminal()

    sm.transition_to(LifecycleState.VALIDATING, reason="Starting input validation")
    assert sm.current_state == LifecycleState.VALIDATING

    sm.transition_to(LifecycleState.PLANNED, reason="Execution plan formed")
    assert sm.current_state == LifecycleState.PLANNED

    sm.transition_to(LifecycleState.EXECUTING, reason="Executing steps")
    assert sm.current_state == LifecycleState.EXECUTING

    sm.transition_to(LifecycleState.VERIFYING, reason="Running critic verification")
    assert sm.current_state == LifecycleState.VERIFYING

    sm.transition_to(LifecycleState.COMPLETED, reason="Execution verified successfully")
    assert sm.current_state == LifecycleState.COMPLETED
    assert sm.is_terminal()
    assert len(sm.history) == 5

def test_invalid_lifecycle_transition_rejection():
    sm = LifecycleStateMachine(initial_state=LifecycleState.REQUESTED)

    # Cannot jump directly from REQUESTED to COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(LifecycleState.COMPLETED)

    # Transition to FAILED is allowed from REQUESTED
    sm.transition_to(LifecycleState.FAILED, reason="Validation error")
    assert sm.current_state == LifecycleState.FAILED
    assert sm.is_terminal()

    # Terminal state cannot transition to any other state
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(LifecycleState.EXECUTING)
