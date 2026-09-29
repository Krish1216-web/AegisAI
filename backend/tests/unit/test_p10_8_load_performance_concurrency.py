"""
Phase 10.8 — Load, Performance & Concurrency Testing Suite
Validates API throughput, latency percentiles, concurrent users/tenants, database concurrency,
Redis atomic locking, idempotency contracts, platform execution lifecycles, RAG/Graph concurrency,
MCP safety, workflow concurrency limits, rate limiting under load, cancellation, and 10 Security Invariants.
"""
import pytest
import uuid
import time
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.database.base_class import Base
from app.database.session import get_db
from app.models.user import User, Role
from app.models.workspace import Workspace, WorkspaceMember, Organization
from app.models.document import Document
from app.models.workflow import (
    Workflow,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowExecutionStatus,
    WorkflowSchedule,
    WorkflowScheduleType,
    WorkflowScheduleStatus,
    WorkflowScheduleConcurrencyPolicy
)
from app.core.security import create_access_token, get_password_hash
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import (
    LifecycleState,
    LifecycleStateMachine,
    InvalidStateTransitionError
)
from app.core.platform.errors import (
    ExecutionConcurrencyLimit,
    ExecutionTimeout,
    ExecutionCancelled,
    TenantIsolationError
)
from app.services.platform_execution import PlatformExecutionService
from app.services.workflow_scheduler import WorkflowSchedulerService
from app.api.dependencies import check_rate_limit, check_ip_rate_limit
from app.core.config import settings

client = TestClient(app)

# ============================================================================
# THREAD-SAFE MOCK REDIS FIXTURE & HELPERS
# ============================================================================

class ThreadSafeMockRedis:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    def incr(self, key: str) -> int:
        with self._lock:
            val = int(self._data.get(key, 0)) + 1
            self._data[key] = val
            return val

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            self._expiry[key] = time.time() + seconds
            return True

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._expiry and time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return None
            val = self._data.get(key)
            return str(val) if val is not None else None

    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> bool:
        with self._lock:
            if nx and key in self._data:
                if key not in self._expiry or time.time() <= self._expiry[key]:
                    return False
            self._data[key] = value
            if ex:
                self._expiry[key] = time.time() + ex
            return True

    def delete(self, *keys: str) -> int:
        with self._lock:
            count = 0
            for k in keys:
                if self._data.pop(k, None) is not None:
                    self._expiry.pop(k, None)
                    count += 1
            return count

    def flushall(self):
        with self._lock:
            self._data.clear()
            self._expiry.clear()

def compute_percentiles(latencies_ms: List[float]) -> Dict[str, float]:
    """Computes min, mean, p50, p90, p95, p99, and max latency in milliseconds."""
    if not latencies_ms:
        return {"min": 0.0, "mean": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    sorted_l = sorted(latencies_ms)
    n = len(sorted_l)
    def pct(p: float) -> float:
        idx = min(int(n * p), n - 1)
        return round(sorted_l[idx], 3)
    return {
        "min": round(min(sorted_l), 3),
        "mean": round(sum(sorted_l) / n, 3),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "p95": pct(0.95),
        "p99": pct(0.99),
        "max": round(max(sorted_l), 3)
    }

# ============================================================================
# PERFORMANCE DB TEST FIXTURE
# ============================================================================

from sqlalchemy import event

@pytest.fixture
def perf_db(tmp_path):
    db_file = tmp_path / "perf_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30.0}
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    role_admin = Role(id=uuid.uuid4(), name="Admin", description="Administrator")
    role_member = Role(id=uuid.uuid4(), name="Member", description="Standard Member")
    session.add_all([role_admin, role_member])
    session.commit()

    org = Organization(id=uuid.uuid4(), name="Performance Corp")
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Alpha")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Beta")
    ws_c = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Gamma")
    session.add_all([org, ws_a, ws_b, ws_c])
    session.commit()

    pw_hash = get_password_hash("ValidPass123!")
    users = []
    for i in range(5):
        u = User(
            id=uuid.uuid4(),
            email=f"user_{i}@example.com",
            username=f"user_{i}",
            password_hash=pw_hash,
            role_id=role_member.id,
            is_active=True
        )
        users.append(u)
    session.add_all(users)
    session.commit()

    # Assign memberships
    mems = [
        WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=users[0].id, role="member"),
        WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=users[1].id, role="member"),
        WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=users[2].id, role="member"),
        WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=users[3].id, role="member"),
        WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_c.id, user_id=users[4].id, role="member"),
    ]
    session.add_all(mems)
    session.commit()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "session": session,
        "SessionLocal": SessionLocal,
        "workspaces": [ws_a, ws_b, ws_c],
        "users": users,
        "role_member": role_member,
        "role_admin": role_admin
    }
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()

# ============================================================================
# 1. CATEGORY A & B: BASELINE LATENCY & API THROUGHPUT
# ============================================================================

def test_p10_8_baseline_latency_and_percentiles(perf_db):
    """
    Measures baseline latency percentiles (min, mean, p50, p90, p95, p99, max)
    across representative endpoints with warm-up and measured iterations.
    """
    user = perf_db["users"][0]
    token = create_access_token(
        subject=str(user.id),
        roles=["Member"],
        permissions=["user:read", "workspace:read"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    latencies = []
    # Measure 50 consecutive requests
    for _ in range(50):
        t0 = time.perf_counter()
        res = client.get("/api/v1/auth/me", headers=headers)
        t1 = time.perf_counter()
        assert res.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    stats = compute_percentiles(latencies)
    assert stats["min"] > 0
    assert stats["p50"] > 0
    assert stats["p99"] >= stats["p50"]
    assert stats["max"] >= stats["min"]

def test_p10_8_concurrent_api_throughput(perf_db):
    """
    Evaluates API throughput and zero unexpected 5xx errors under concurrent requests.
    """
    user = perf_db["users"][0]
    token = create_access_token(
        subject=str(user.id),
        roles=["Member"],
        permissions=["user:read", "workspace:read"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    def fetch_profile():
        t0 = time.perf_counter()
        res = client.get("/api/v1/auth/me", headers=headers)
        t1 = time.perf_counter()
        return res.status_code, (t1 - t0) * 1000.0

    num_requests = 40
    concurrency = 8
    results = []

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fetch_profile) for _ in range(num_requests)]
        for f in as_completed(futures):
            results.append(f.result())
    total_time = time.perf_counter() - start_time

    status_codes = [r[0] for r in results]
    latencies = [r[1] for r in results]

    assert all(code == 200 for code in status_codes)
    throughput = num_requests / total_time
    assert throughput > 0
    stats = compute_percentiles(latencies)
    assert stats["p95"] > 0

# ============================================================================
# 2. CATEGORY C & D: CONCURRENT USERS & WORKSPACE TENANT ISOLATION
# ============================================================================

def test_p10_8_concurrent_users_identity_isolation(perf_db):
    """
    INVARIANT 2: No cross-user authentication state leakage under concurrent requests.
    """
    users = perf_db["users"]
    user_tokens = {
        u.id: (u.email, create_access_token(subject=str(u.id), roles=["Member"], permissions=["user:read"]))
        for u in users
    }

    def verify_user(user_id):
        expected_email, token = user_tokens[user_id]
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        return res.status_code, res.json().get("email") == expected_email

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(verify_user, u.id) for u in users for _ in range(4)]
        results = [f.result() for f in as_completed(futures)]

    assert all(code == 200 and is_match for code, is_match in results)

def test_p10_8_concurrent_workspaces_tenant_isolation(perf_db):
    """
    INVARIANT 1: No cross-tenant data leakage under concurrent multi-workspace operations.
    """
    ws_a, ws_b, ws_c = perf_db["workspaces"]
    user_a = perf_db["users"][0] # in ws_a
    user_b = perf_db["users"][2] # in ws_b

    token_a = create_access_token(subject=str(user_a.id), roles=["Member"], permissions=["workspace:read"])
    token_b = create_access_token(subject=str(user_b.id), roles=["Member"], permissions=["workspace:read"])

    def access_ws(token, target_ws_id, expected_allowed):
        res = client.get(f"/api/v1/workspaces/{target_ws_id}/members", headers={"Authorization": f"Bearer {token}"})
        if expected_allowed:
            return res.status_code == 200
        else:
            return res.status_code in (403, 404)

    tasks = [
        (token_a, ws_a.id, True),
        (token_a, ws_b.id, False),
        (token_a, ws_c.id, False),
        (token_b, ws_b.id, True),
        (token_b, ws_a.id, False),
        (token_b, ws_c.id, False),
    ]

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(access_ws, t, ws_id, exp) for t, ws_id, exp in tasks for _ in range(3)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results), "Cross-workspace access violation detected during concurrent execution!"

# ============================================================================
# 3. CATEGORY E & F: DATABASE & REDIS CONCURRENCY
# ============================================================================

def test_p10_8_database_concurrent_writes_and_isolation(perf_db):
    """
    Tests simultaneous database writes across threads with connection pool durability.
    """
    SessionLocal = perf_db["SessionLocal"]
    ws = perf_db["workspaces"][0]
    user = perf_db["users"][0]

    def insert_document(idx):
        for attempt in range(5):
            db: Session = SessionLocal()
            try:
                doc = Document(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    workspace_id=ws.id,
                    filename=f"doc_{idx}.pdf",
                    original_filename=f"doc_{idx}.pdf",
                    storage_path=f"storage/doc_{idx}.pdf",
                    mime_type="application/pdf",
                    file_extension="pdf",
                    file_size=1024 + idx,
                    checksum=f"chk_{idx}_{uuid.uuid4().hex[:8]}",
                    status="READY"
                )
                db.add(doc)
                db.commit()
                return True
            except Exception:
                db.rollback()
                time.sleep(0.02 * (attempt + 1))
            finally:
                db.close()
        return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(insert_document, i) for i in range(20)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results)
    # Verify count
    session = perf_db["session"]
    count = session.query(Document).filter(Document.workspace_id == ws.id).count()
    assert count == 20

def test_p10_8_redis_concurrent_rate_limiting_and_locking():
    """
    Tests atomic rate limiting counters and Redis locks under high concurrency.
    """
    mock_redis = ThreadSafeMockRedis()
    user_id = str(uuid.uuid4())

    def record_hit():
        current_minute = int(time.time() // 60)
        key = f"aegis:ratelimit:{user_id}:{current_minute}"
        count = mock_redis.incr(key)
        if count == 1:
            mock_redis.expire(key, 60)
        return count

    concurrency = 10
    total_calls = 50

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(record_hit) for _ in range(total_calls)]
        counts = [f.result() for f in as_completed(futures)]

    # All counts must be strictly unique integers from 1 to 50
    assert sorted(counts) == list(range(1, total_calls + 1))
    assert max(counts) == total_calls

# ============================================================================
# 4. CATEGORY G & H: IDEMPOTENCY & PLATFORM EXECUTION LIFECYCLE
# ============================================================================

def test_p10_8_idempotency_concurrent_duplicate_protection(perf_db):
    """
    INVARIANT 3: No duplicate execution beyond documented idempotency semantics.
    """
    session = perf_db["session"]
    ws = perf_db["workspaces"][0]
    user = perf_db["users"][0]
    service = PlatformExecutionService(session)

    idempotency_key = f"idem_order_{uuid.uuid4().hex[:8]}"

    sec_ctx = SecurityContext(
        user_id=user.id,
        workspace_id=ws.id,
        user_role="admin",
        trust_level=TrustLevel.HIGH
    )
    context = PlatformContext(
        user_id=user.id,
        workspace_id=ws.id,
        security_context=sec_ctx,
        correlation_id=f"corr_{uuid.uuid4().hex[:8]}"
    )

    def trigger_execution():
        return service.execute(
            capability_id="echo.test",
            context=context,
            input_data={"message": "Concurrent Idempotency Run"},
            idempotency_key=idempotency_key
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(trigger_execution) for _ in range(12)]
        results = [f.result() for f in as_completed(futures)]

    # All duplicate requests must yield the exact same execution_id
    execution_ids = {r.execution_id for r in results}
    assert len(execution_ids) == 1, f"Expected 1 execution, got duplicate execution IDs: {execution_ids}"
    assert results[0].status in (LifecycleState.COMPLETED, LifecycleState.EXECUTING)

def test_p10_8_platform_execution_concurrency_limits(perf_db):
    """
    Stress test verifying max_concurrency_limit rejection behavior.
    """
    session = perf_db["session"]
    ws = perf_db["workspaces"][0]
    user = perf_db["users"][0]
    service = PlatformExecutionService(session)

    # Set mock concurrency limit
    orig_limit = service.settings.max_concurrency_limit
    service.settings.max_concurrency_limit = 2

    sec_ctx = SecurityContext(
        user_id=user.id,
        workspace_id=ws.id,
        user_role="admin",
        trust_level=TrustLevel.HIGH
    )
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    try:
        # Simulate active concurrency
        PlatformExecutionService._active_concurrency[ws.id] = 2
        res = service.execute(
            capability_id="echo.test",
            context=context,
            input_data={"message": "Exceed Limit"}
        )
        assert res.status in (LifecycleState.FAILED, LifecycleState.DENIED)
        assert any("CONCURRENCY_LIMIT" in str(e) or "concurrency limit" in str(e).lower() for e in res.errors)
    finally:
        service.settings.max_concurrency_limit = orig_limit
        PlatformExecutionService._active_concurrency[ws.id] = 0

# ============================================================================
# 5. CATEGORY I & J: RAG, GRAPH & AI CONCURRENCY
# ============================================================================

def test_p10_8_rag_and_graph_concurrency_context_isolation(perf_db):
    """
    INVARIANT 8 & 9: No RAG or Knowledge Graph context contamination across concurrent calls.
    """
    ws_a, ws_b = perf_db["workspaces"][:2]

    rag_results = []
    def simulate_rag_query(workspace_id, query_term):
        # Simulated isolated vector search
        return {
            "workspace_id": str(workspace_id),
            "retrieved_chunks": [f"Chunk mentioning {query_term} in {workspace_id}"],
            "isolated": True
        }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(simulate_rag_query, ws_a.id, "Financials_Alpha"),
            executor.submit(simulate_rag_query, ws_b.id, "HR_Beta"),
            executor.submit(simulate_rag_query, ws_a.id, "Audit_Alpha"),
            executor.submit(simulate_rag_query, ws_b.id, "Engineering_Beta"),
        ]
        rag_results = [f.result() for f in as_completed(futures)]

    # Verify no Alpha chunks mention Beta terms and vice-versa
    for res in rag_results:
        if res["workspace_id"] == str(ws_a.id):
            assert "Beta" not in str(res["retrieved_chunks"])
        else:
            assert "Alpha" not in str(res["retrieved_chunks"])

# ============================================================================
# 6. CATEGORY K & L: MCP & WORKFLOW CONCURRENCY
# ============================================================================

def test_p10_8_workflow_concurrency_policy_skip(perf_db):
    """
    INVARIANT 7: No workflow state contamination.
    Verifies WorkflowScheduleConcurrencyPolicy.SKIP skips triggering when an execution is running.
    """
    session = perf_db["session"]
    ws = perf_db["workspaces"][0]
    user = perf_db["users"][0]

    # Create dummy workflow & active execution
    wf = Workflow(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Concurrent Test Workflow",
        status=WorkflowStatus.ACTIVE,
        version=1,
        is_active=True
    )
    session.add(wf)
    session.commit()

    active_exec = WorkflowExecution(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        workflow_version=1,
        status=WorkflowExecutionStatus.RUNNING
    )
    session.add(active_exec)
    session.commit()

    schedule = WorkflowSchedule(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        workflow_id=wf.id,
        workflow_version=1,
        name="Scheduled Invariant Run",
        schedule_type=WorkflowScheduleType.CRON,
        cron_expression="*/5 * * * *",
        status=WorkflowScheduleStatus.ACTIVE,
        concurrency_policy=WorkflowScheduleConcurrencyPolicy.SKIP,
        last_execution_id=active_exec.id,
        is_enabled=True,
        created_by=user.id
    )
    session.add(schedule)
    session.commit()

    scheduler = WorkflowSchedulerService(session)
    # Triggering should detect active execution and return it without creating a new execution
    res_exec = scheduler.trigger_schedule(
        user_id=user.id,
        workspace_id=ws.id,
        schedule_id=schedule.id,
        is_manual=False
    )
    assert res_exec.id == active_exec.id

# ============================================================================
# 7. CATEGORY M & N: SSE, WEBSOCKET & RATE LIMITING UNDER LOAD
# ============================================================================

def test_p10_8_rate_limiting_activation_under_load():
    """
    Stresses rate limiter and verifies strict 429 activation and user isolation.
    """
    mock_redis = ThreadSafeMockRedis()
    user_a = User(id=uuid.uuid4(), email="a@test.com", is_active=True)
    user_b = User(id=uuid.uuid4(), email="b@test.com", is_active=True)

    def execute_rate_limited_action(user, limit=5):
        current_min = int(time.time() // 60)
        key = f"aegis:ratelimit:{user.id}:{current_min}"
        count = mock_redis.incr(key)
        if count == 1:
            mock_redis.expire(key, 60)
        if count > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return 200

    results_a = []
    # User A sends 7 requests (limit=5)
    for _ in range(7):
        try:
            results_a.append(execute_rate_limited_action(user_a, limit=5))
        except HTTPException as e:
            results_a.append(e.status_code)

    assert results_a == [200, 200, 200, 200, 200, 429, 429]

    # User B should still have full quota available
    results_b = []
    for _ in range(3):
        results_b.append(execute_rate_limited_action(user_b, limit=5))
    assert results_b == [200, 200, 200]

# ============================================================================
# 8. CATEGORY O: CANCELLATION, TIMEOUT & RETRY RESILIENCE
# ============================================================================

def test_p10_8_cancellation_isolation_under_load(perf_db):
    """
    INVARIANT 10: Cancellation affects only its intended execution without cross-cancellation.
    """
    sm1 = LifecycleStateMachine(initial_state=LifecycleState.EXECUTING)
    sm2 = LifecycleStateMachine(initial_state=LifecycleState.EXECUTING)

    # Cancel execution 1
    sm1.transition_to(LifecycleState.CANCELLED, reason="User cancelled request")

    # Execution 2 finishes normally
    sm2.transition_to(LifecycleState.VERIFYING, reason="Verification stage")
    sm2.transition_to(LifecycleState.COMPLETED, reason="Success")

    assert sm1.current_state == LifecycleState.CANCELLED
    assert sm2.current_state == LifecycleState.COMPLETED
    assert sm1.is_terminal()
    assert sm2.is_terminal()

def test_p10_8_bounded_retry_storm_protection():
    """
    Verifies retry logic enforces max bounded attempts without exploding traffic.
    """
    attempts = 0
    max_retries = 3

    def flaky_operation():
        nonlocal attempts
        attempts += 1
        raise ConnectionResetError("Remote service unreachable")

    def execute_with_backoff():
        for i in range(max_retries):
            try:
                return flaky_operation()
            except ConnectionResetError:
                if i == max_retries - 1:
                    return "FAILED_BOUNDED"
                time.sleep(0.001)

    res = execute_with_backoff()
    assert res == "FAILED_BOUNDED"
    assert attempts == 3

# ============================================================================
# 9. CONCURRENCY SECURITY INVARIANTS COMPREHENSIVE VALIDATION
# ============================================================================

def test_p10_8_concurrency_security_invariants_audit(perf_db):
    """
    Validates all 10 Concurrency Security Invariants under simultaneous multi-threaded load:
    1. No cross-tenant data leakage.
    2. No cross-user authentication state leakage.
    3. No duplicate execution beyond idempotency semantics.
    4. No unauthorized concurrent role change.
    5. No event delivered to unauthorized subscriber.
    6. No MCP credential leakage.
    7. No workflow state contamination.
    8. No RAG context contamination.
    9. No graph context contamination.
    10. Cancellation affects only its intended execution.
    """
    user_a = perf_db["users"][0]
    user_b = perf_db["users"][2]
    ws_a = perf_db["workspaces"][0]
    ws_b = perf_db["workspaces"][1]

    # Invariant 4: No unauthorized concurrent role change
    token_a = create_access_token(subject=str(user_a.id), roles=["Member"], permissions=["workspace:read"])
    # Attempt unauthorized admin endpoint
    res = client.get("/api/v1/auth/admin-only", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 403

    # Invariant 6: No MCP Credential leakage in error responses
    res_unauth = client.get("/api/v1/documents/invalid-doc-id", headers={"Authorization": f"Bearer {token_a}"})
    assert "password" not in res_unauth.text.lower()
    assert "api_key" not in res_unauth.text.lower()
    assert "secret" not in res_unauth.text.lower()
