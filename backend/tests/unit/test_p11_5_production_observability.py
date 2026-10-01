import uuid
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.correlation import (
    get_correlation_context,
    set_correlation_context,
    clear_correlation_context,
    sanitize_header_value,
    CorrelationMiddleware
)
from app.core.metrics import MetricsRegistry, metrics_registry
from app.core.mcp.security import CredentialStore
from app.services.operational_alerts import OperationalAlertEngine, operational_alert_engine
from app.models.user import User, Role
from app.models.job import BackgroundJob, JobStatus, JobPriority
from app.models.audit import AuditLog
from app.database.session import get_db
from app.api.dependencies import get_current_user


@pytest.fixture(autouse=True)
def clean_observability_state():
    """Reset metrics and alerts before and after each test."""
    metrics_registry.reset()
    operational_alert_engine.reset()
    clear_correlation_context()
    yield
    metrics_registry.reset()
    operational_alert_engine.reset()
    clear_correlation_context()


# =====================================================================
# 1. CORRELATION CONTEXT & SANITIZATION TESTS
# =====================================================================

def test_sanitize_header_value_valid():
    val = "req-12345-abcdef"
    assert sanitize_header_value(val) == "req-12345-abcdef"


def test_sanitize_header_value_strips_crlf_and_control_chars():
    malicious = "req-123\r\nInjected-Header: evil\x00\x08"
    sanitized = sanitize_header_value(malicious)
    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert "\x00" not in sanitized
    assert "req-123" in sanitized


def test_sanitize_header_value_truncates_long_input():
    long_val = "a" * 300
    sanitized = sanitize_header_value(long_val, max_length=128)
    assert len(sanitized) == 128


def test_correlation_context_set_get_clear():
    assert all(v is None for v in get_correlation_context().values())
    set_correlation_context(
        request_id="req-1",
        correlation_id="corr-1",
        execution_id="exec-1",
        job_id="job-1",
        workflow_id="wf-1",
    )
    ctx = get_correlation_context()
    assert ctx["request_id"] == "req-1"
    assert ctx["correlation_id"] == "corr-1"
    assert ctx["execution_id"] == "exec-1"
    assert ctx["job_id"] == "job-1"
    assert ctx["workflow_id"] == "wf-1"

    clear_correlation_context()
    assert all(v is None for v in get_correlation_context().values())


def test_correlation_middleware_generates_and_propagates_headers():
    client = TestClient(app)
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None


def test_correlation_middleware_preserves_incoming_correlation_id():
    client = TestClient(app)
    custom_corr = "trace-client-xyz-987"
    response = client.get("/health/liveness", headers={"X-Correlation-ID": custom_corr})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == custom_corr


# =====================================================================
# 2. METRICS REGISTRY TESTS
# =====================================================================

def test_metrics_registry_records_requests_and_latency():
    registry = MetricsRegistry()
    registry.record_request(method="GET", route="/api/v1/users", status_code=200, duration_ms=50.0)
    registry.record_request(method="GET", route="/api/v1/users", status_code=200, duration_ms=100.0)
    registry.record_request(method="POST", route="/api/v1/users", status_code=500, duration_ms=150.0)

    data = registry.get_request_metrics()
    assert data["total_requests"] == 3
    assert data["status_code_distribution"]["2xx"] == 2
    assert data["status_code_distribution"]["5xx"] == 1
    assert data["latency_ms"]["min"] == 50.0
    assert data["latency_ms"]["max"] == 150.0
    assert data["latency_ms"]["p50"] == 100.0


def test_metrics_registry_normalizes_high_cardinality_uuids():
    middleware = CorrelationMiddleware(app)
    u1 = str(uuid.uuid4())
    norm_path = middleware._normalize_route(f"/api/v1/workspaces/{u1}")
    assert norm_path == "/api/v1/workspaces/:id"

    norm_num = middleware._normalize_route("/api/v1/items/4567")
    assert norm_num == "/api/v1/items/:id"


def test_metrics_registry_records_worker_lifecycle():
    registry = MetricsRegistry()
    registry.record_job_lifecycle("queued")
    registry.record_job_lifecycle("started")
    registry.record_job_lifecycle("succeeded")
    registry.record_job_lifecycle("retried")
    registry.record_job_lifecycle("dead_lettered")
    registry.record_job_lifecycle("cancelled")
    registry.record_job_lifecycle("stale_recovered")

    wm = registry.get_infrastructure_metrics()["worker"]
    assert wm["jobs_queued"] == 1
    assert wm["jobs_started"] == 1
    assert wm["jobs_succeeded"] == 1
    assert wm["jobs_retried"] == 1
    assert wm["jobs_dead_lettered"] == 1
    assert wm["jobs_cancelled"] == 1
    assert wm["jobs_stale_recovered"] == 1


def test_metrics_registry_records_scheduler_and_domains():
    registry = MetricsRegistry()
    registry.record_scheduler_event("cycle")
    registry.record_scheduler_event("schedule_triggered", count=3)
    registry.record_scheduler_event("duplicate_suppressed", count=2)

    sm = registry.get_infrastructure_metrics()["scheduler"]
    assert sm["cycles_total"] == 1
    assert sm["schedules_triggered"] == 3
    assert sm["duplicate_suppressions"] == 2

    registry.record_capability_telemetry("mcp", "tool", count=2)
    registry.record_capability_telemetry("mcp", "security_block", count=1)
    registry.record_capability_telemetry("rag", "query", count=5)
    registry.record_capability_telemetry("rag", "retrieval", count=4)
    registry.record_capability_telemetry("graph", "traversal", count=3)
    registry.record_capability_telemetry("agent", "invocation", count=1)
    registry.record_capability_telemetry("workflow", "run", count=2)

    dm = registry.get_domain_telemetry()
    assert dm["mcp"]["tool_invocations"] == 2
    assert dm["mcp"]["security_blocks"] == 1
    assert dm["rag"]["queries"] == 5
    assert dm["rag"]["retrievals"] == 4
    assert dm["graph"]["traversals"] == 3
    assert dm["agent"]["invocations"] == 1
    assert dm["workflow"]["runs_total"] == 2


# =====================================================================
# 3. OPERATIONAL ALERT ENGINE TESTS
# =====================================================================

def test_operational_alert_trigger_and_deduplication():
    engine = OperationalAlertEngine(cooldown_seconds=300)
    alert1 = engine.trigger_alert(
        rule_name="TEST_RULE",
        severity="CRITICAL",
        title="Test Critical Alert",
        description="Threshold violated",
        metric_name="test_metric",
        current_value=99.0,
        threshold_value=50.0,
        entity_id="entity_1"
    )
    assert alert1.status == "TRIGGERED"
    assert alert1.current_value == 99.0

    # Triggering duplicate with same rule & entity while active should update instead of creating new
    alert2 = engine.trigger_alert(
        rule_name="TEST_RULE",
        severity="CRITICAL",
        title="Test Critical Alert Updated",
        description="Threshold violated again",
        metric_name="test_metric",
        current_value=105.0,
        threshold_value=50.0,
        entity_id="entity_1"
    )
    assert alert1.alert_id == alert2.alert_id
    assert alert2.current_value == 105.0
    assert len(engine.get_alerts()) == 1


def test_operational_alert_acknowledge_and_resolve():
    engine = OperationalAlertEngine()
    alert = engine.trigger_alert(
        rule_name="QUEUE_SATURATION",
        severity="WARNING",
        title="Queue full",
        description="Queue full description",
        metric_name="queue_depth",
        current_value=600,
        threshold_value=500
    )
    assert alert.status == "TRIGGERED"

    ack = engine.acknowledge_alert(alert.alert_id, acknowledged_by="admin-user-id")
    assert ack is not None
    assert ack.status == "ACKNOWLEDGED"
    assert ack.acknowledged_by == "admin-user-id"
    assert ack.acknowledged_at is not None

    res = engine.resolve_alert(alert.alert_id, resolved_by="admin-user-id")
    assert res is not None
    assert res.status == "RESOLVED"
    assert res.resolved_by == "admin-user-id"
    assert res.resolved_at is not None


def test_operational_alert_rule_evaluation():
    engine = OperationalAlertEngine()
    registry = MetricsRegistry()

    # Seed 5xx error rate
    for _ in range(8):
        registry.record_request(method="GET", route="/api/v1/test", status_code=200, duration_ms=10.0)
    for _ in range(2):
        registry.record_request(method="GET", route="/api/v1/test", status_code=500, duration_ms=10.0)

    # Seed dead letters
    for _ in range(6):
        registry.record_job_lifecycle("dead_lettered")

    # Seed DB exhaustion
    registry.record_db_pool_exhaustion()

    # Evaluate
    triggered = engine.evaluate_rules(metrics=registry)
    rule_names = {a.rule_name for a in triggered}
    assert "HIGH_5XX_ERROR_RATE" in rule_names
    assert "DEAD_LETTER_BURST" in rule_names
    assert "DATABASE_POOL_SATURATION" in rule_names


def test_operational_alert_scrubs_secrets_in_title_and_metadata():
    engine = OperationalAlertEngine()
    secret_title = "Connection failed with Bearer sk-1234567890abcdef1234567890abcdef"
    secret_meta = {"db_password": "supersecretpassword123", "normal_info": "safe"}

    alert = engine.trigger_alert(
        rule_name="SECRET_LEAK_CHECK",
        severity="WARNING",
        title=secret_title,
        description="Leaked token in error",
        metric_name="secret_metric",
        current_value=1.0,
        threshold_value=0.0,
        metadata=secret_meta
    )

    assert "supersecretpassword123" not in str(alert.metadata)
    assert alert.metadata["db_password"] == "[REDACTED]"
    assert alert.metadata["normal_info"] == "safe"


# =====================================================================
# 4. OBSERVABILITY API ENDPOINTS & INCIDENT TIMELINE TESTS
# =====================================================================

@pytest.fixture
def mock_admin_user():
    role_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        email="admin@aegisai.test",
        username="admin_test",
        password_hash="fake_hash",
        role_id=role_id,
        is_active=True,
    )
    user.role = Role(id=role_id, name="admin")
    return user


@pytest.fixture
def mock_db_session():
    db = MagicMock(spec=Session)
    return db


def test_observability_overview_endpoint(mock_admin_user, mock_db_session):
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        metrics_registry.record_request("GET", "/api/v1/test", 200, 45.0)
        res = client.get("/api/v1/observability/overview")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "total_requests" in data
        assert "latency_p95_ms" in data
        assert "active_alerts" in data
        assert data["total_requests"] >= 1
    finally:
        app.dependency_overrides.clear()


def test_observability_metrics_endpoints(mock_admin_user, mock_db_session):
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        metrics_registry.record_request("GET", "/api/v1/items", 200, 15.0)
        metrics_registry.record_capability_telemetry("workflow", "run", count=1)

        # Requests metrics
        res_req = client.get("/api/v1/observability/metrics/requests")
        assert res_req.status_code == 200
        assert res_req.json()["total_requests"] >= 1

        # Infrastructure metrics
        res_infra = client.get("/api/v1/observability/metrics/infrastructure")
        assert res_infra.status_code == 200
        assert "database" in res_infra.json()
        assert "worker" in res_infra.json()

        # Domains metrics
        res_dom = client.get("/api/v1/observability/metrics/domains")
        assert res_dom.status_code == 200
        assert "workflow" in res_dom.json()
    finally:
        app.dependency_overrides.clear()


def test_observability_alerts_lifecycle_api(mock_admin_user, mock_db_session):
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        alert = operational_alert_engine.trigger_alert(
            rule_name="HIGH_5XX_ERROR_RATE",
            severity="CRITICAL",
            title="High Error Rate",
            description="5xx rate exceeded",
            metric_name="http_5xx_rate",
            current_value=0.15,
            threshold_value=0.05
        )

        # List alerts
        res_list = client.get("/api/v1/observability/alerts")
        assert res_list.status_code == 200
        alerts = res_list.json()["alerts"]
        assert len(alerts) >= 1
        assert alerts[0]["alert_id"] == alert.alert_id

        # Acknowledge alert
        res_ack = client.post(f"/api/v1/observability/alerts/{alert.alert_id}/acknowledge")
        assert res_ack.status_code == 200
        assert res_ack.json()["status"] == "ACKNOWLEDGED"

        # Resolve alert
        res_res = client.post(f"/api/v1/observability/alerts/{alert.alert_id}/resolve")
        assert res_res.status_code == 200
        assert res_res.json()["status"] == "RESOLVED"
    finally:
        app.dependency_overrides.clear()


def test_observability_incident_timeline_endpoint(mock_admin_user, mock_db_session):
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    corr_id = f"incident-trace-{uuid.uuid4()}"
    operational_alert_engine.trigger_alert(
        rule_name="INCIDENT_ALERT",
        severity="CRITICAL",
        title="Incident Alert",
        description="Incident Alert Desc",
        metric_name="incident_metric",
        current_value=1.0,
        threshold_value=0.0,
        metadata={"correlation_id": corr_id}
    )

    try:
        res = client.get(f"/api/v1/observability/incident/timeline?query_id={corr_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["query_id"] == corr_id
        assert data["total_events"] >= 1
        assert data["events"][0]["source"] == "alert"
    finally:
        app.dependency_overrides.clear()


# =====================================================================
# 5. DIAGNOSTIC HEALTH & DEPENDENCY PROBE TESTS
# =====================================================================

def test_health_dependencies_probe():
    client = TestClient(app)
    with patch("app.main.check_redis_health", return_value=True):
        res = client.get("/health/dependencies")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "dependencies" in data
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "worker_cluster" in data["dependencies"]
        assert "storage" in data["dependencies"]


def test_metrics_registry_percentiles_edge_cases():
    assert MetricsRegistry._calculate_percentile([], 50) == 0.0
    assert MetricsRegistry._calculate_percentile([42.0], 50) == 42.0
    assert MetricsRegistry._calculate_percentile([10.0, 20.0, 30.0, 40.0, 50.0], 90) == 46.0


def test_metrics_registry_route_cardinality_bounded():
    registry = MetricsRegistry()
    for i in range(250):
        registry.record_request(method="GET", route=f"/route_{i}", status_code=200, duration_ms=10.0)
    data = registry.get_request_metrics()
    assert len(data["routes"]) <= registry.MAX_ROUTES_TRACKED


def test_operational_alert_filters():
    engine = OperationalAlertEngine()
    a1 = engine.trigger_alert("R1", "CRITICAL", "Crit Alert", "Desc", "m1", 1.0, 0.0, entity_id="e1")
    a2 = engine.trigger_alert("R2", "WARNING", "Warn Alert", "Desc", "m2", 1.0, 0.0, entity_id="e2")
    engine.resolve_alert(a2.alert_id, resolved_by="user1")

    crit_only = engine.get_alerts(severity_filter="CRITICAL")
    assert len(crit_only) == 1
    assert crit_only[0].alert_id == a1.alert_id

    resolved_only = engine.get_alerts(status_filter="RESOLVED")
    assert len(resolved_only) == 1
    assert resolved_only[0].alert_id == a2.alert_id


def test_observability_unauthorized_user_forbidden():
    client = TestClient(app)
    # User with viewer role and no workspace_id
    role = Role(id=uuid.uuid4(), name="viewer")
    unauthorized_user = User(
        id=uuid.uuid4(),
        email="viewer@test.com",
        username="viewer_test",
        password_hash="fake_hash",
        role_id=role.id,
        is_active=True,
    )
    unauthorized_user.role = role

    app.dependency_overrides[get_current_user] = lambda: unauthorized_user
    try:
        res = client.get("/api/v1/observability/overview")
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_health_readiness_probe_success_and_failure(mock_db_session):
    client = TestClient(app)
    app.dependency_overrides[get_db] = lambda: mock_db_session

    # Healthy scenario
    with patch("app.main.check_redis_health", return_value=True):
        res = client.get("/health/readiness")
        assert res.status_code == 200
        assert res.json()["status"] == "ready"

    # Unhealthy Redis scenario
    with patch("app.main.check_redis_health", return_value=False):
        res = client.get("/health/readiness")
        assert res.status_code == 503

    app.dependency_overrides.clear()
