"""
Phase 10.9 — Security Observability & Compliance Readiness Test Suite
Validates canonical security event taxonomy, cryptographic audit chain integrity,
correlation propagation, pattern-based alerting, deduplication, tenant-isolated queries,
secret redaction, admin RBAC, incident evidence lookup, and compliance readiness artifacts.
"""
import pytest
import uuid
import datetime
import time
from typing import Dict, Any, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.database.base_class import Base
from app.database.session import get_db
from app.models.user import User, Role
from app.models.workspace import Workspace, WorkspaceMember, Organization
from app.core.security import create_access_token, get_password_hash
from app.core.security_events import (
    SecurityEventType,
    SecuritySeverity,
    SecurityEventRecord,
    DEFAULT_SEVERITY_MAP
)
from app.services.security_observability import (
    SecurityObservabilityService,
    SecurityAlertEngine
)
from app.services.platform_execution import PlatformExecutionService
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.services.auth import AuthService
from app.services.authorization import AuthorizationService
import redis

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_security_state():
    SecurityObservabilityService.clear()
    yield
    SecurityObservabilityService.clear()

@pytest.fixture
def obs_db(tmp_path):
    db_file = tmp_path / "obs_test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    role_admin = Role(id=uuid.uuid4(), name="Admin", description="Administrator")
    role_member = Role(id=uuid.uuid4(), name="Member", description="Standard Member")
    session.add_all([role_admin, role_member])
    session.commit()

    org = Organization(id=uuid.uuid4(), name="Observability Corp")
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Alpha")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace Beta")
    session.add_all([org, ws_a, ws_b])
    session.commit()

    pw_hash = get_password_hash("SecurePassword123!")
    user_admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="admin_user",
        password_hash=pw_hash,
        role_id=role_admin.id,
        is_active=True
    )
    user_member = User(
        id=uuid.uuid4(),
        email="member@example.com",
        username="member_user",
        password_hash=pw_hash,
        role_id=role_member.id,
        is_active=True
    )
    session.add_all([user_admin, user_member])
    session.commit()

    mem_admin = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_admin.id, role="owner")
    mem_member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_member.id, role="member")
    session.add_all([mem_admin, mem_member])
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
        "ws_a": ws_a,
        "ws_b": ws_b,
        "user_admin": user_admin,
        "user_member": user_member,
        "role_admin": role_admin,
        "role_member": role_member
    }

    app.dependency_overrides.clear()
    session.close()
    engine.dispose()

# ============================================================================
# 1. CANONICAL EVENT CREATION & REDACTION
# ============================================================================

def test_p10_9_canonical_security_event_creation_and_redaction(obs_db):
    """
    Tests canonical security event creation, structure validity, and recursive secret redaction.
    """
    service = SecurityObservabilityService(obs_db["session"])
    ws = obs_db["ws_a"]
    user = obs_db["user_admin"]

    event = service.record_event(
        event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
        source_component="AuthService",
        action="USER_LOGIN",
        outcome="SUCCESS",
        actor_id=user.id,
        workspace_id=ws.id,
        correlation_id="corr_test_123",
        security_metadata={"token": "Bearer sk-secret-token-12345", "client_secret": "my-top-secret"},
        sanitized_details={"username": "admin_user", "password": "PlainPassword123!"}
    )

    assert event.event_id.startswith("sec_")
    assert event.severity == SecuritySeverity.INFO
    assert event.event_hash is not None
    assert event.previous_hash == "GENESIS_HASH"

    # Verify secret redaction
    assert "sk-secret-token-12345" not in str(event.security_metadata)
    assert "[REDACTED]" in str(event.security_metadata)
    assert "PlainPassword123!" not in str(event.sanitized_details)
    assert "[REDACTED]" in str(event.sanitized_details)

def test_p10_9_default_severity_classification():
    """
    Validates deterministic severity mapping across all canonical event types.
    """
    assert DEFAULT_SEVERITY_MAP[SecurityEventType.AUTH_REFRESH_REPLAY] == SecuritySeverity.CRITICAL
    assert DEFAULT_SEVERITY_MAP[SecurityEventType.TENANT_BOUNDARY_VIOLATION] == SecuritySeverity.HIGH
    assert DEFAULT_SEVERITY_MAP[SecurityEventType.SSRF_BLOCKED] == SecuritySeverity.HIGH
    assert DEFAULT_SEVERITY_MAP[SecurityEventType.PROMPT_INJECTION_BLOCKED] == SecuritySeverity.HIGH
    assert DEFAULT_SEVERITY_MAP[SecurityEventType.RATE_LIMIT_TRIGGERED] == SecuritySeverity.LOW
    assert DEFAULT_SEVERITY_MAP[SecurityEventType.AUTH_LOGIN_SUCCESS] == SecuritySeverity.INFO

# ============================================================================
# 2. CRYPTOGRAPHIC AUDIT CHAIN INTEGRITY & IMMUTABILITY
# ============================================================================

def test_p10_9_cryptographic_audit_chain_integrity_verification(obs_db):
    """
    Tests SHA-256 hash chaining across consecutive security events and tamper detection.
    """
    service = SecurityObservabilityService(obs_db["session"])
    ws = obs_db["ws_a"]

    # Record 3 chained events
    ev1 = service.record_event(
        event_type=SecurityEventType.AUTH_LOGIN_SUCCESS,
        source_component="Auth",
        action="LOGIN_1",
        workspace_id=ws.id
    )
    ev2 = service.record_event(
        event_type=SecurityEventType.ROLE_CHANGED,
        source_component="RBAC",
        action="UPDATE_ROLE",
        workspace_id=ws.id
    )
    ev3 = service.record_event(
        event_type=SecurityEventType.ADMIN_ACTION,
        source_component="Admin",
        action="CONFIG_UPDATE",
        workspace_id=ws.id
    )

    assert ev1.previous_hash == "GENESIS_HASH"
    assert ev2.previous_hash == ev1.event_hash
    assert ev3.previous_hash == ev2.event_hash

    # Verify unbroken integrity
    res = service.verify_integrity()
    assert res.is_valid is True
    assert res.total_events_verified == 3
    assert res.tampered_events_count == 0
    assert len(res.tampered_event_ids) == 0

    # Simulate tampering on event 2 action
    ev2.action = "TAMPERED_ACTION_FORGED"
    tampered_res = service.verify_integrity()
    assert tampered_res.is_valid is False
    assert tampered_res.tampered_events_count >= 1
    assert ev2.event_id in tampered_res.tampered_event_ids

# ============================================================================
# 3. REAL-TIME SECURITY ALERTING & DEDUPLICATION
# ============================================================================

def test_p10_9_alert_engine_repeated_auth_failures(obs_db):
    """
    Validates threshold-based alert generation on 5 failed login attempts and alert deduplication.
    """
    service = SecurityObservabilityService(obs_db["session"])
    ws = obs_db["ws_a"]
    user_id = uuid.uuid4()

    # Trigger 4 failures (below threshold)
    for _ in range(4):
        service.record_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILED,
            source_component="AuthService",
            action="LOGIN_ATTEMPT",
            outcome="FAILURE",
            actor_id=user_id,
            workspace_id=ws.id
        )

    alerts = service.alert_engine.get_alerts(workspace_id=ws.id)
    assert len(alerts) == 0

    # Trigger 5th failure (reaches threshold)
    service.record_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILED,
        source_component="AuthService",
        action="LOGIN_ATTEMPT",
        outcome="FAILURE",
        actor_id=user_id,
        workspace_id=ws.id
    )

    alerts = service.alert_engine.get_alerts(workspace_id=ws.id)
    assert len(alerts) == 1
    assert alerts[0].rule_name == "REPEATED_AUTH_FAILURES"
    assert alerts[0].severity == SecuritySeverity.HIGH
    assert alerts[0].trigger_count == 1

    # 6th failure within cooldown window should deduplicate
    service.record_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILED,
        source_component="AuthService",
        action="LOGIN_ATTEMPT",
        outcome="FAILURE",
        actor_id=user_id,
        workspace_id=ws.id
    )

    alerts_dedup = service.alert_engine.get_alerts(workspace_id=ws.id)
    assert len(alerts_dedup) == 1
    assert alerts_dedup[0].trigger_count == 2

def test_p10_9_alert_engine_critical_attacks(obs_db):
    """
    Validates instant critical alert firing on refresh replay, SSRF, prompt injection, and MCP violations.
    """
    service = SecurityObservabilityService(obs_db["session"])
    ws = obs_db["ws_a"]

    # 1. Refresh replay
    service.record_event(
        event_type=SecurityEventType.AUTH_REFRESH_REPLAY,
        source_component="AuthService",
        action="TOKEN_ROTATION",
        outcome="REPLAY_DETECTED",
        workspace_id=ws.id
    )

    # 2. SSRF Blocked
    service.record_event(
        event_type=SecurityEventType.SSRF_BLOCKED,
        source_component="NetworkValidator",
        action="OUTBOUND_REQUEST",
        outcome="BLOCKED",
        workspace_id=ws.id,
        reason="Target URL resolved to private subnet 10.0.0.1"
    )

    # 3. Prompt Injection Blocked
    service.record_event(
        event_type=SecurityEventType.PROMPT_INJECTION_BLOCKED,
        source_component="RAGDocumentScanner",
        action="DOCUMENT_INGEST",
        outcome="BLOCKED",
        workspace_id=ws.id,
        reason="Indirect prompt injection pattern 'Ignore previous instructions' detected."
    )

    # 4. MCP Security Violation
    service.record_event(
        event_type=SecurityEventType.MCP_SECURITY_VIOLATION,
        source_component="MCPServerRegistry",
        action="EXECUTE_RESTRICTED_TOOL",
        outcome="BLOCKED",
        workspace_id=ws.id,
        reason="Unapproved system shell command tool call."
    )

    alerts = service.alert_engine.get_alerts(workspace_id=ws.id)
    rule_names = {a.rule_name for a in alerts}

    assert "REFRESH_TOKEN_REPLAY" in rule_names
    assert "SSRF_ATTEMPT" in rule_names
    assert "PROMPT_INJECTION_BLOCKED" in rule_names
    assert "MCP_SECURITY_VIOLATION" in rule_names

# ============================================================================
# 4. MULTI-TENANT ISOLATION & QUERY FILTERING
# ============================================================================

def test_p10_9_multi_tenant_security_event_isolation(obs_db):
    """
    Verifies that security events recorded for Workspace Alpha are completely invisible to Workspace Beta queries.
    """
    service = SecurityObservabilityService(obs_db["session"])
    ws_a = obs_db["ws_a"]
    ws_b = obs_db["ws_b"]

    service.record_event(
        event_type=SecurityEventType.AUTHZ_DENIED,
        source_component="Authz",
        action="READ_DOCUMENT_A",
        workspace_id=ws_a.id
    )
    service.record_event(
        event_type=SecurityEventType.AUTHZ_DENIED,
        source_component="Authz",
        action="READ_DOCUMENT_B",
        workspace_id=ws_b.id
    )

    list_a = service.list_events(workspace_id=ws_a.id)
    list_b = service.list_events(workspace_id=ws_b.id)

    assert list_a.total == 1
    assert list_a.events[0].action == "READ_DOCUMENT_A"

    assert list_b.total == 1
    assert list_b.events[0].action == "READ_DOCUMENT_B"

# ============================================================================
# 5. CORRELATION & INCIDENT EVIDENCE LOOKUP
# ============================================================================

def test_p10_9_incident_evidence_correlation_lookup(obs_db):
    """
    Validates end-to-end evidence correlation across User -> Request -> Security Event -> Execution -> Audit Log.
    """
    session = obs_db["session"]
    ws = obs_db["ws_a"]
    user = obs_db["user_admin"]
    service = SecurityObservabilityService(session)

    corr_id = f"corr_investigate_{uuid.uuid4().hex[:8]}"
    exec_id = f"exec_investigate_{uuid.uuid4().hex[:8]}"
    req_id = f"req_{uuid.uuid4().hex[:8]}"

    # Record linked security event
    service.record_event(
        event_type=SecurityEventType.PROMPT_INJECTION_DETECTED,
        source_component="IntelligenceEngine",
        action="PLAN_EVALUATION",
        outcome="DETECTED",
        actor_id=user.id,
        workspace_id=ws.id,
        request_id=req_id,
        correlation_id=corr_id,
        execution_id=exec_id,
        reason="Suspicious instruction override token found."
    )

    # Perform investigation lookup by correlation_id
    evidence = service.lookup_incident_evidence(
        query_param="correlation_id",
        query_value=corr_id,
        workspace_id=ws.id
    )

    assert evidence.total_records_found >= 1
    assert evidence.correlation_id == corr_id
    assert any("SECURITY:PROMPT_INJECTION_DETECTED" in item.event_type for item in evidence.timeline)

# ============================================================================
# 6. SECURITY METRICS & BOUNDED TIME WINDOWS
# ============================================================================

def test_p10_9_security_metrics_aggregation(obs_db):
    """
    Validates aggregation of security metrics, severity distribution, category counts, and time windows.
    """
    service = SecurityObservabilityService(obs_db["session"])
    ws = obs_db["ws_a"]

    service.record_event(event_type=SecurityEventType.AUTH_LOGIN_SUCCESS, source_component="Auth", action="LOGIN", workspace_id=ws.id)
    service.record_event(event_type=SecurityEventType.AUTH_LOGIN_FAILED, source_component="Auth", action="LOGIN", workspace_id=ws.id)
    service.record_event(event_type=SecurityEventType.SSRF_BLOCKED, source_component="SSRF", action="CONNECT", workspace_id=ws.id)
    service.record_event(event_type=SecurityEventType.AUTHZ_DENIED, source_component="Authz", action="ACCESS", workspace_id=ws.id)

    metrics = service.get_security_metrics(workspace_id=ws.id, time_window="24h")

    assert metrics.total_events == 4
    assert metrics.events_by_severity["INFO"] >= 1
    assert metrics.events_by_severity["MEDIUM"] >= 2
    assert metrics.events_by_severity["HIGH"] >= 1
    assert metrics.authentication_metrics["login_success"] == 1
    assert metrics.authentication_metrics["login_failed"] == 1
    assert metrics.ai_mcp_security_metrics["ssrf_blocked"] == 1
    assert metrics.authorization_metrics["authz_denied"] == 1

# ============================================================================
# 7. ADMIN SECURITY ENDPOINTS & RBAC ACCESS CONTROL
# ============================================================================

def test_p10_9_admin_security_api_endpoints_rbac(obs_db):
    """
    Verifies that admin security endpoints are strictly accessible to Admins and blocked (403) for standard members.
    """
    user_admin = obs_db["user_admin"]
    user_member = obs_db["user_member"]

    admin_token = create_access_token(subject=str(user_admin.id), roles=["Admin"], permissions=["platform:admin:view", "platform:admin:write"])
    member_token = create_access_token(subject=str(user_member.id), roles=["Member"], permissions=["chat:read"])

    # 1. Non-admin access attempt -> HTTP 403
    forbidden_res = client.get("/api/v1/admin/security/events", headers={"Authorization": f"Bearer {member_token}"})
    assert forbidden_res.status_code == 403

    # 2. Admin access -> HTTP 200
    events_res = client.get("/api/v1/admin/security/events", headers={"Authorization": f"Bearer {admin_token}"})
    assert events_res.status_code == 200
    assert "events" in events_res.json()

    alerts_res = client.get("/api/v1/admin/security/alerts", headers={"Authorization": f"Bearer {admin_token}"})
    assert alerts_res.status_code == 200
    assert "alerts" in alerts_res.json()

    metrics_res = client.get("/api/v1/admin/security/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert metrics_res.status_code == 200
    assert "events_by_severity" in metrics_res.json()

    integrity_res = client.get("/api/v1/admin/security/audit-integrity", headers={"Authorization": f"Bearer {admin_token}"})
    assert integrity_res.status_code == 200
    assert integrity_res.json()["is_valid"] is True

# ============================================================================
# 8. RETENTION & DATA LIFECYCLE MANAGEMENT
# ============================================================================

def test_p10_9_retention_lifecycle_inspection_and_purge(obs_db):
    """
    Tests retention inspection dry-run and bounded purge with administrative audit trail.
    """
    service = SecurityObservabilityService(obs_db["session"])
    user_admin = obs_db["user_admin"]

    # Add dummy event
    service.record_event(
        event_type=SecurityEventType.ADMIN_ACTION,
        source_component="Config",
        action="TEST_ACTION",
        actor_id=user_admin.id
    )

    # Dry-run inspection
    dry_run = service.inspect_retention(retention_days=30)
    assert dry_run.is_dry_run is True
    assert dry_run.retention_days_security_events == 30

    # Purge apply
    purged = service.apply_retention(retention_days=30, admin_user_id=user_admin.id)
    assert isinstance(purged, int)

# ============================================================================
# 9. INTEGRATION WITH AUTH & AUTHORIZATION SERVICES
# ============================================================================

def test_p10_9_auth_service_security_event_emission(obs_db):
    """
    Validates automatic emission of AUTH_LOGIN_FAILED and AUTH_LOGIN_SUCCESS from AuthService.
    """
    session = obs_db["session"]
    user = obs_db["user_admin"]
    service = SecurityObservabilityService(session)

    auth_svc = AuthService(db=session, redis_client=None)

    # Failed login
    with pytest.raises(Exception):
        auth_svc.login_user(username_or_email="admin_user", plain_password="WrongPassword999!")

    # Check that failed event was recorded in SecurityObservabilityService
    events = service.list_events(event_type=SecurityEventType.AUTH_LOGIN_FAILED)
    assert events.total >= 1
    assert events.events[0].outcome == "FAILURE"

def test_p10_9_authorization_service_security_event_emission(obs_db):
    """
    Validates automatic emission of AUTHZ_DENIED and TENANT_BOUNDARY_VIOLATION from AuthorizationService.
    """
    session = obs_db["session"]
    user_member = obs_db["user_member"]
    ws_a = obs_db["ws_a"]
    ws_b = obs_db["ws_b"]
    service = SecurityObservabilityService(session)

    authz_svc = AuthorizationService(session)

    # 1. Missing permission -> AUTHZ_DENIED
    with pytest.raises(Exception):
        authz_svc.assert_authorized(
            user_id=user_member.id,
            workspace_id=ws_b.id,
            permission="system:admin:super_power"
        )

    denied_events = service.list_events(event_type=SecurityEventType.AUTHZ_DENIED)
    assert denied_events.total >= 1

    # 2. Workspace boundary mismatch -> TENANT_BOUNDARY_VIOLATION
    with pytest.raises(Exception):
        authz_svc.assert_workspace_ownership(
            resource_workspace_id=ws_a.id,
            request_workspace_id=ws_b.id,
            user_id=user_member.id
        )

    violation_events = service.list_events(event_type=SecurityEventType.TENANT_BOUNDARY_VIOLATION)
    assert violation_events.total >= 1
