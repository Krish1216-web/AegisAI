import pytest
import uuid
import datetime
import time
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.job import BackgroundJob, JobStatus, JobPriority, JobErrorCategory
from app.models.workflow import (
    Workflow,
    WorkflowNodeType,
    WorkflowSchedule,
    WorkflowScheduleType,
    WorkflowScheduleStatus
)
from app.schemas.workflow import WorkflowCreate, WorkflowNodeCreate, WorkflowEdgeCreate, WorkflowScheduleCreate
from app.services.workflow import WorkflowService
from app.services.workflow_scheduler import WorkflowSchedulerService
from app.services.worker_service import (
    WorkerService,
    calculate_exponential_backoff,
    classify_error_category
)
from app.core.queue import QueueManager
from app.services.scheduler_daemon import SchedulerDaemon
from app.worker import WorkerDaemon
from app.core.platform.errors import (
    TenantIsolationError,
    CapabilityPermissionDenied,
    InvalidExecutionInput,
    ExecutionTimeout
)
from app.main import app
from app.api.dependencies import get_current_user


from sqlalchemy.pool import StaticPool

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_queue_mgr():
    mock = MagicMock(spec=QueueManager)
    mock.redis = MagicMock()
    mock.enqueue.return_value = True
    mock.dequeue.return_value = None
    mock.poll_delayed_jobs.return_value = []
    mock.acquire_lock.return_value = True
    mock.renew_lock.return_value = True
    mock.release_lock.return_value = True
    mock.get_active_workers.return_value = [{"worker_id": "test_w1", "status": "healthy"}]
    mock.get_queue_depth.return_value = {"critical": 0, "high": 0, "default": 0, "low": 0, "delayed": 0}
    return mock


@pytest.fixture
def worker_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Worker Test Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    member_role = Role(id=uuid.uuid4(), name="member")
    db_session.add_all([org, admin_role, member_role])
    db_session.flush()

    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Worker WS 1")
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Worker WS 2")

    user1 = User(
        id=uuid.uuid4(),
        email="worker_admin@test.com",
        username="worker_admin",
        password_hash="hashed_pw",
        role_id=admin_role.id,
        is_active=True
    )
    user2 = User(
        id=uuid.uuid4(),
        email="worker_user2@test.com",
        username="worker_user2",
        password_hash="hashed_pw",
        role_id=member_role.id,
        is_active=True
    )
    db_session.add_all([ws1, ws2, user1, user2])
    db_session.flush()

    mem1 = WorkspaceMember(workspace_id=ws1.id, user_id=user1.id, role="admin")
    mem2 = WorkspaceMember(workspace_id=ws2.id, user_id=user2.id, role="member")
    db_session.add_all([mem1, mem2])
    db_session.commit()

    return {
        "org": org,
        "ws1": ws1,
        "ws2": ws2,
        "user1": user1,
        "user2": user2
    }


# ==============================================================================
# 1. Job Model, Enums & Exponential Backoff Unit Tests
# ==============================================================================

def test_job_model_creation_and_defaults(db_session: Session, worker_setup):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]

    job = BackgroundJob(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        created_by=user.id,
        job_type="test.job",
        payload={"param": 123}
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.status == JobStatus.QUEUED
    assert job.priority == 50
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.scheduled_at is not None
    assert job.created_at is not None


def test_job_status_enum_values():
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.CLAIMED.value == "claimed"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.SUCCEEDED.value == "succeeded"
    assert JobStatus.FAILED.value == "failed"
    assert JobStatus.CANCEL_REQUESTED.value == "cancel_requested"
    assert JobStatus.CANCELLED.value == "cancelled"
    assert JobStatus.DEAD_LETTERED.value == "dead_lettered"
    assert JobStatus.RETRY_WAIT.value == "retry_wait"


def test_exponential_backoff_calculation():
    d1 = calculate_exponential_backoff(attempt=1, base_seconds=2.0, max_seconds=300.0, jitter=False)
    d2 = calculate_exponential_backoff(attempt=2, base_seconds=2.0, max_seconds=300.0, jitter=False)
    d3 = calculate_exponential_backoff(attempt=3, base_seconds=2.0, max_seconds=300.0, jitter=False)
    d_max = calculate_exponential_backoff(attempt=10, base_seconds=2.0, max_seconds=50.0, jitter=False)

    assert d1 == 2.0
    assert d2 == 4.0
    assert d3 == 8.0
    assert d_max == 50.0

    # With jitter
    d_jitter = calculate_exponential_backoff(attempt=2, base_seconds=2.0, jitter=True)
    assert 4.0 < d_jitter <= 5.0


def test_classify_error_category():
    assert classify_error_category(TenantIsolationError("Tenant cross breach")) == JobErrorCategory.PERMANENT_AUTH
    assert classify_error_category(CapabilityPermissionDenied("Denial")) == JobErrorCategory.PERMANENT_AUTH
    assert classify_error_category(InvalidExecutionInput("Bad format")) == JobErrorCategory.PERMANENT_VALIDATION
    assert classify_error_category(ExecutionTimeout("Timeout after 60s")) == JobErrorCategory.TIMEOUT
    assert classify_error_category(RuntimeError("Prompt injection blocked")) == JobErrorCategory.PERMANENT_SECURITY
    assert classify_error_category(ConnectionError("Redis connection lost")) == JobErrorCategory.TRANSIENT
    assert classify_error_category(Exception("Some unexpected error")) == JobErrorCategory.UNKNOWN


# ==============================================================================
# 2. WorkerService Enqueue & Deduplication Tests
# ==============================================================================

def test_enqueue_job_success(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(
        workspace_id=ws.id,
        created_by=user.id,
        job_type="custom.task",
        payload={"task_id": "abc"},
        priority=80
    )

    assert job.id is not None
    assert job.status == JobStatus.QUEUED
    assert job.priority == 80
    assert mock_queue_mgr.enqueue.called


def test_enqueue_job_idempotency_deduplication(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    key = "unique-operation-key-123"
    job1 = svc.enqueue_job(
        workspace_id=ws.id,
        created_by=user.id,
        job_type="custom.task",
        payload={"num": 1},
        idempotency_key=key
    )

    job2 = svc.enqueue_job(
        workspace_id=ws.id,
        created_by=user.id,
        job_type="custom.task",
        payload={"num": 2},
        idempotency_key=key
    )

    assert job1.id == job2.id
    total_jobs = db_session.query(BackgroundJob).filter(BackgroundJob.idempotency_key == key).count()
    assert total_jobs == 1


def test_enqueue_job_secret_scrubbing(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(
        workspace_id=ws.id,
        created_by=user.id,
        job_type="sensitive.task",
        payload={
            "safe_arg": "value123",
            "api_key": "sk-real-live-secret-key-12345",
            "db_password": "super-secret-password"
        }
    )

    assert job.payload["safe_arg"] == "value123"
    assert job.payload["api_key"] == "[REDACTED]"
    assert job.payload["db_password"] == "[REDACTED]"


def test_enqueue_job_delayed_scheduling(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    job = svc.enqueue_job(
        workspace_id=ws.id,
        created_by=user.id,
        job_type="delayed.task",
        payload={},
        scheduled_at=future_time
    )

    job_sched_ts = int(job.scheduled_at.replace(tzinfo=datetime.timezone.utc).timestamp()) if not job.scheduled_at.tzinfo else int(job.scheduled_at.timestamp())
    assert abs(job_sched_ts - int(future_time.timestamp())) <= 1
    assert mock_queue_mgr.enqueue.call_args[1]["delay_seconds"] > 500


def test_enqueue_job_invalid_workspace(db_session: Session, worker_setup, mock_queue_mgr):
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    fake_ws_id = uuid.uuid4()
    with pytest.raises(ValueError) as exc:
        svc.enqueue_job(
            workspace_id=fake_ws_id,
            created_by=user.id,
            job_type="task",
            payload={}
        )
    assert "does not exist" in str(exc.value)


# ==============================================================================
# 3. Atomic Claiming & Priority Ordering Tests
# ==============================================================================

def test_atomic_claim_next_job(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="task.a", payload={})

    claimed = svc.claim_next_job(worker_id="worker-node-1")
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JobStatus.CLAIMED
    assert claimed.worker_id == "worker-node-1"
    assert claimed.lock_token is not None


def test_atomic_claim_priority_ordering(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job_low = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="low", payload={}, priority=10)
    job_high = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="high", payload={}, priority=90)
    job_med = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="med", payload={}, priority=50)

    # Claim 1 should be highest priority
    claimed1 = svc.claim_next_job(worker_id="w1")
    assert claimed1.id == job_high.id

    # Claim 2 should be medium priority
    claimed2 = svc.claim_next_job(worker_id="w1")
    assert claimed2.id == job_med.id

    # Claim 3 should be low priority
    claimed3 = svc.claim_next_job(worker_id="w1")
    assert claimed3.id == job_low.id


def test_claim_respects_tenant_concurrency_limit(db_session: Session, worker_setup, mock_queue_mgr):
    ws1 = worker_setup["ws1"]
    ws2 = worker_setup["ws2"]
    user1 = worker_setup["user1"]
    user2 = worker_setup["user2"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    # Put 2 running jobs in WS1
    running1 = svc.enqueue_job(workspace_id=ws1.id, created_by=user1.id, job_type="ws1.run1", payload={})
    running2 = svc.enqueue_job(workspace_id=ws1.id, created_by=user1.id, job_type="ws1.run2", payload={})
    c1 = svc.claim_next_job(worker_id="w1", max_tenant_concurrency=2)
    c2 = svc.claim_next_job(worker_id="w2", max_tenant_concurrency=2)

    # Third job for WS1, and first job for WS2
    job_ws1_pending = svc.enqueue_job(workspace_id=ws1.id, created_by=user1.id, job_type="ws1.pending", payload={}, priority=90)
    job_ws2_pending = svc.enqueue_job(workspace_id=ws2.id, created_by=user2.id, job_type="ws2.pending", payload={}, priority=50)

    # Next claim with max_tenant_concurrency=2 should skip WS1 and pick WS2
    claimed = svc.claim_next_job(worker_id="w3", max_tenant_concurrency=2)
    assert claimed is not None
    assert claimed.id == job_ws2_pending.id
    assert claimed.workspace_id == ws2.id


# ==============================================================================
# 4. Job Execution, Retries, and Dead-Lettering Tests
# ==============================================================================

def test_process_job_success_custom_handler(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="custom.calc", payload={"x": 10, "y": 20})
    claimed = svc.claim_next_job(worker_id="worker-1")

    def calc_handler(j: BackgroundJob, session: Session):
        return {"sum": j.payload["x"] + j.payload["y"]}

    result_job = svc.process_job(job_id=claimed.id, worker_id="worker-1", custom_handler=calc_handler)
    assert result_job.status == JobStatus.SUCCEEDED
    assert result_job.result == {"sum": 30}
    assert result_job.completed_at is not None


def test_process_job_transient_error_exponential_backoff(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="flaky.task", payload={}, max_attempts=3)
    claimed = svc.claim_next_job(worker_id="worker-1")

    def flaky_handler(j: BackgroundJob, session: Session):
        raise ConnectionError("Temporary redis glitch")

    result_job = svc.process_job(job_id=claimed.id, worker_id="worker-1", custom_handler=flaky_handler)
    assert result_job.status == JobStatus.RETRY_WAIT
    assert result_job.attempts == 1
    assert result_job.next_retry_at is not None
    assert result_job.error_category == JobErrorCategory.TRANSIENT
    assert "Temporary redis glitch" in result_job.last_error


def test_process_job_exceeded_max_attempts_dead_lettering(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="failing.task", payload={}, max_attempts=2)
    job.attempts = 1
    db_session.commit()

    claimed = svc.claim_next_job(worker_id="worker-1")

    def failing_handler(j: BackgroundJob, session: Session):
        raise TimeoutError("Execution timed out")

    result_job = svc.process_job(job_id=claimed.id, worker_id="worker-1", custom_handler=failing_handler)
    assert result_job.status == JobStatus.DEAD_LETTERED
    assert result_job.attempts == 2
    assert result_job.completed_at is not None


def test_process_job_permanent_auth_error_no_retry(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="auth.task", payload={}, max_attempts=5)
    claimed = svc.claim_next_job(worker_id="worker-1")

    def auth_fail_handler(j: BackgroundJob, session: Session):
        raise CapabilityPermissionDenied("Unauthorized action")

    result_job = svc.process_job(job_id=claimed.id, worker_id="worker-1", custom_handler=auth_fail_handler)
    assert result_job.status == JobStatus.DEAD_LETTERED
    assert result_job.attempts == 1  # No further retries allowed
    assert result_job.error_category == JobErrorCategory.PERMANENT_AUTH


def test_error_sanitization_in_failure(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="secret.error", payload={}, max_attempts=1)
    claimed = svc.claim_next_job(worker_id="worker-1")

    def secret_error_handler(j: BackgroundJob, session: Session):
        raise RuntimeError("Failed communicating with upstream service using api_key=sk-secret-live-token-12345")

    result_job = svc.process_job(job_id=claimed.id, worker_id="worker-1", custom_handler=secret_error_handler)
    assert result_job.status == JobStatus.DEAD_LETTERED
    assert "sk-secret-live-token-12345" not in result_job.last_error
    assert "[REDACTED]" in result_job.last_error


# ==============================================================================
# 5. Cancellation & Heartbeat Recovery Tests
# ==============================================================================

def test_cancel_queued_job(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="cancel.me", payload={})
    cancelled_job = svc.cancel_job(job_id=job.id, workspace_id=ws.id, user_id=user.id)

    assert cancelled_job.status == JobStatus.CANCELLED
    assert cancelled_job.completed_at is not None


def test_cancel_running_job(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="running.cancel", payload={})
    claimed = svc.claim_next_job(worker_id="w1")

    # Set to running
    claimed.status = JobStatus.RUNNING
    db_session.commit()

    cancelled_job = svc.cancel_job(job_id=claimed.id, workspace_id=ws.id, user_id=user.id)
    assert cancelled_job.status == JobStatus.CANCEL_REQUESTED


def test_cancel_job_tenant_boundary_violation(db_session: Session, worker_setup, mock_queue_mgr):
    ws1 = worker_setup["ws1"]
    ws2 = worker_setup["ws2"]
    user1 = worker_setup["user1"]
    user2 = worker_setup["user2"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job_ws1 = svc.enqueue_job(workspace_id=ws1.id, created_by=user1.id, job_type="tenant.job", payload={})

    # User 2 in WS2 cannot cancel WS1 job
    with pytest.raises(ValueError) as exc:
        svc.cancel_job(job_id=job_ws1.id, workspace_id=ws2.id, user_id=user2.id)
    assert "not found in workspace" in str(exc.value)


def test_update_heartbeat(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    job = svc.enqueue_job(workspace_id=ws.id, created_by=user.id, job_type="hb.job", payload={})
    claimed = svc.claim_next_job(worker_id="worker-node-x")

    assert svc.update_heartbeat(claimed.id, worker_id="worker-node-x") is True
    # Wrong worker ID fails
    assert svc.update_heartbeat(claimed.id, worker_id="wrong-worker") is False


def test_recover_stale_jobs_retry_and_dead_letter(db_session: Session, worker_setup, mock_queue_mgr):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]
    svc = WorkerService(db_session, queue_mgr=mock_queue_mgr)

    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120)

    # Job 1: 0 attempts, should retry
    job1 = BackgroundJob(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        created_by=user.id,
        job_type="stale1",
        status=JobStatus.RUNNING,
        worker_id="dead-worker",
        heartbeat_at=past_time,
        attempts=0,
        max_attempts=3,
        payload={}
    )

    # Job 2: 2 attempts (max 2), should dead-letter
    job2 = BackgroundJob(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        created_by=user.id,
        job_type="stale2",
        status=JobStatus.CLAIMED,
        worker_id="dead-worker",
        heartbeat_at=past_time,
        attempts=2,
        max_attempts=2,
        payload={}
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    recovered = svc.recover_stale_jobs(stale_timeout_seconds=60)
    assert len(recovered) == 2

    db_session.refresh(job1)
    db_session.refresh(job2)

    assert job1.status == JobStatus.RETRY_WAIT
    assert job1.attempts == 1
    assert job2.status == JobStatus.DEAD_LETTERED


# ==============================================================================
# 6. QueueManager & Distributed Coordination Tests
# ==============================================================================

def test_queue_manager_priority_routing():
    qm = QueueManager()
    assert qm._get_priority_queue(100) == "aegis:queue:critical"
    assert qm._get_priority_queue(80) == "aegis:queue:critical"
    assert qm._get_priority_queue(50) == "aegis:queue:high"
    assert qm._get_priority_queue(30) == "aegis:queue:default"
    assert qm._get_priority_queue(10) == "aegis:queue:low"


def test_queue_manager_distributed_locks():
    mock_redis = MagicMock()
    mock_redis.set.return_value = True
    mock_redis.eval.return_value = 1

    qm = QueueManager(redis_client=mock_redis)

    assert qm.acquire_lock("lock:key", "token123", ttl_seconds=10) is True
    assert qm.renew_lock("lock:key", "token123", ttl_seconds=10) is True
    assert qm.release_lock("lock:key", "token123") is True


def test_queue_manager_heartbeat_and_depth():
    mock_redis = MagicMock()
    mock_redis.llen.return_value = 5
    mock_redis.zcard.return_value = 2

    qm = QueueManager(redis_client=mock_redis)
    qm.register_worker_heartbeat("worker_1", {"uptime": 100})
    assert mock_redis.set.called

    depths = qm.get_queue_depth()
    assert depths["default"] == 5
    assert depths["delayed"] == 2


# ==============================================================================
# 7. SchedulerDaemon & WorkflowSchedulerService Integration Tests
# ==============================================================================

def test_workflow_scheduler_enqueue_due_schedules(db_session: Session, worker_setup):
    ws = worker_setup["ws1"]
    user = worker_setup["user1"]

    wf_svc = WorkflowService(db_session)
    sched_svc = WorkflowSchedulerService(db_session)

    wf = wf_svc.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Scheduled Workflow Flow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="end_1")
            ]
        )
    )

    sched = sched_svc.create_schedule(
        user.id,
        ws.id,
        WorkflowScheduleCreate(
            workflow_id=wf.id,
            name="Worker Cron Task",
            schedule_type="cron",
            cron_expression="0 12 * * *"
        )
    )

    # Force next_run_at to past
    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    sched.next_run_at = past_time
    db_session.commit()

    enqueued_jobs = sched_svc.enqueue_due_schedules(max_batch=10)
    assert len(enqueued_jobs) == 1
    assert enqueued_jobs[0].job_type == "workflow.execution"
    assert enqueued_jobs[0].workspace_id == ws.id

    db_session.refresh(sched)
    next_dt = sched.next_run_at.replace(tzinfo=datetime.timezone.utc) if sched.next_run_at.tzinfo is None else sched.next_run_at
    past_dt = past_time.replace(tzinfo=datetime.timezone.utc) if past_time.tzinfo is None else past_time
    assert next_dt > past_dt


def test_scheduler_daemon_cycle_as_leader(db_session: Session, mock_queue_mgr):
    daemon = SchedulerDaemon(
        db_session_factory=lambda: db_session,
        queue_mgr=mock_queue_mgr,
        instance_id="leader_node"
    )

    result = daemon.run_cycle()
    assert result["is_leader"] is True
    assert "enqueued_schedules" in result
    assert "recovered_stale" in result


def test_scheduler_daemon_cycle_as_standby(db_session: Session, mock_queue_mgr):
    mock_queue_mgr.acquire_lock.return_value = False
    mock_queue_mgr.renew_lock.return_value = False

    daemon = SchedulerDaemon(
        db_session_factory=lambda: db_session,
        queue_mgr=mock_queue_mgr,
        instance_id="standby_node"
    )

    result = daemon.run_cycle()
    assert result["is_leader"] is False
    assert result["status"] == "standby"


def test_worker_daemon_health_metrics():
    worker = WorkerDaemon(worker_id="health_test_worker", concurrency=8, enable_scheduler=False)
    status = worker.get_health_status()

    assert status["status"] == "healthy"
    assert status["worker_id"] == "health_test_worker"
    assert status["concurrency"] == 8
    assert status["active_jobs_count"] == 0
    assert status["scheduler_enabled"] is False


# ==============================================================================
# 8. API Endpoints Tests
# ==============================================================================

def test_jobs_api_crud_flow(db_session: Session, worker_setup):
    user = worker_setup["user1"]
    ws = worker_setup["ws1"]

    # Override get_current_user and get_db dependencies
    app.dependency_overrides[get_current_user] = lambda: user
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: db_session

    client = TestClient(app)

    # 1. Create Job via POST /jobs/
    resp = client.post(
        f"/api/v1/jobs/?workspace_id={ws.id}",
        json={
            "job_type": "api.test.job",
            "payload": {"hello": "world"},
            "priority": 50
        }
    )
    assert resp.status_code == 201, resp.text
    job_data = resp.json()
    job_id = job_data["id"]
    assert job_data["job_type"] == "api.test.job"
    assert job_data["status"] == "queued"

    # 2. List Jobs via GET /jobs/
    list_resp = client.get(f"/api/v1/jobs/?workspace_id={ws.id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 3. Get Job by ID via GET /jobs/{id}
    get_resp = client.get(f"/api/v1/jobs/{job_id}?workspace_id={ws.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == job_id

    # 4. Cancel Job via POST /jobs/{id}/cancel
    cancel_resp = client.post(f"/api/v1/jobs/{job_id}/cancel?workspace_id={ws.id}")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # 5. Cluster Health via GET /jobs/cluster/health
    health_resp = client.get("/api/v1/jobs/cluster/health")
    assert health_resp.status_code == 200
    assert "queue_depths" in health_resp.json()

    # Clean up overrides
    app.dependency_overrides.clear()
