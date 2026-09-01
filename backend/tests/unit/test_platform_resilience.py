import pytest
import uuid
import time
import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.events import PlatformEvent, PlatformEventType, PlatformEventDispatcher
from app.core.platform.execution_result import PlatformExecutionResult
from app.core.platform.capability import (
    PlatformCapability,
    CapabilityMetadata,
    CapabilityType,
    platform_capability_registry
)
from app.services.platform_execution import PlatformExecutionService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def resilience_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Resilience Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Resilience")
    user = User(
        id=uuid.uuid4(),
        email="res_user@test.com",
        username="res_user",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_idempotency_key_prevents_duplicate_execution(db_session: Session, resilience_setup):
    ws_id = resilience_setup["ws"].id
    user_id = resilience_setup["user"].id
    service = PlatformExecutionService(db_session)

    context = PlatformContext(
        workspace_id=ws_id,
        user_id=user_id,
        correlation_id="corr_idem_1",
        security_context=SecurityContext(workspace_id=ws_id, user_id=user_id, user_role="admin")
    )

    # First execution with idempotency key
    res1 = service.execute(
        capability_id="echo.test",
        input_data={"message": "hello idempotency"},
        context=context,
        idempotency_key="idemp_key_1001"
    )
    assert res1.status == LifecycleState.COMPLETED
    assert "echo" in res1.output

    # Second execution with same idempotency key
    res2 = service.execute(
        capability_id="echo.test",
        input_data={"message": "hello idempotency"},
        context=context,
        idempotency_key="idemp_key_1001"
    )
    assert res2.status == LifecycleState.COMPLETED
    assert res2.execution_id == res1.execution_id
    assert "echo" in res2.output

def test_concurrent_idempotency_race_safety(db_session: Session, resilience_setup):
    ws_id = resilience_setup["ws"].id
    user_id = resilience_setup["user"].id
    service = PlatformExecutionService(db_session)

    context = PlatformContext(
        workspace_id=ws_id,
        user_id=user_id,
        correlation_id="corr_conc_1",
        security_context=SecurityContext(workspace_id=ws_id, user_id=user_id, user_role="admin")
    )

    def run_worker(idx):
        return service.execute(
            capability_id="echo.test",
            input_data={"message": f"msg_{idx}"},
            context=context,
            idempotency_key="shared_idemp_key_parallel"
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_worker, i) for i in range(5)]
        results = [f.result() for f in futures]

    # All executions must succeed with LifecycleState.COMPLETED
    assert len(results) == 5
    for r in results:
        assert r.status == LifecycleState.COMPLETED

def test_fast_execution_cancellation(db_session: Session, resilience_setup):
    ws_id = resilience_setup["ws"].id
    user_id = resilience_setup["user"].id
    service = PlatformExecutionService(db_session)

    context = PlatformContext(
        workspace_id=ws_id,
        user_id=user_id,
        correlation_id="corr_cancel_1",
        security_context=SecurityContext(workspace_id=ws_id, user_id=user_id, user_role="admin")
    )

    # Seed execution
    res = service.execute(
        capability_id="echo.test",
        input_data={"message": "test cancel"},
        context=context
    )

    # Cancel execution
    cancelled = service.cancel_execution(
        execution_id=res.execution_id,
        user_id=user_id,
        workspace_id=ws_id,
        reason="Operator abort"
    )
    assert cancelled.status == LifecycleState.CANCELLED
    assert len(cancelled.errors) >= 1
    assert "Operator abort" in cancelled.errors[0]["message"]

def test_unavailable_capability_deterministic_failure(db_session: Session, resilience_setup):
    ws_id = resilience_setup["ws"].id
    user_id = resilience_setup["user"].id
    service = PlatformExecutionService(db_session)

    context = PlatformContext(
        workspace_id=ws_id,
        user_id=user_id,
        correlation_id="corr_unavail_1",
        security_context=SecurityContext(workspace_id=ws_id, user_id=user_id, user_role="admin")
    )

    result = service.execute(
        capability_id="nonexistent.unknown.capability",
        input_data={"q": "foo"},
        context=context
    )

    assert result.status == LifecycleState.FAILED
    assert len(result.errors) >= 1
    assert "not registered" in result.errors[0]["message"].lower() or "not found" in result.errors[0]["message"].lower()

def test_event_dispatcher_subscriber_resilience():
    # Defective subscriber that throws an unhandled exception
    def broken_subscriber(evt: PlatformEvent):
        raise RuntimeError("Defective subscriber crash!")

    PlatformEventDispatcher.subscribe(PlatformEventType.LIFECYCLE_EVENT, broken_subscriber)

    evt = PlatformEvent(
        event_type=PlatformEventType.LIFECYCLE_EVENT,
        correlation_id="corr_disp_resilience",
        workspace_id=uuid.uuid4(),
        source_component="test",
        payload={"status": "ok"}
    )

    # Dispatching should swallow subscriber errors without crashing the main application flow
    PlatformEventDispatcher.emit(evt)
    PlatformEventDispatcher.clear_handlers()
