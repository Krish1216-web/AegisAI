import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.provenance import ProvenanceItem, ProvenanceSourceType, ProvenanceTrustLevel
from app.core.platform.execution_result import PlatformExecutionResult
from app.core.platform.observability import (
    PlatformObservabilityService,
    CapabilityHealth,
    BottleneckClassification
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
def obs_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Obs Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, viewer_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS B")
    
    user_a = User(
        id=uuid.uuid4(),
        email="user_a@test.com",
        username="user_a",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user_b = User(
        id=uuid.uuid4(),
        email="user_b@test.com",
        username="user_b",
        password_hash="pw",
        role_id=viewer_role.id,
        is_active=True
    )
    db_session.add_all([ws_a, ws_b, user_a, user_b])
    db_session.flush()

    mem_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="admin")
    mem_b = WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role="viewer")
    db_session.add_all([mem_a, mem_b])
    db_session.commit()

    return {"user_a": user_a, "user_b": user_b, "ws_a": ws_a, "ws_b": ws_b}

def test_overview_metrics_generation_and_tenant_isolation(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    ws_b = obs_setup["ws_b"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    # Seed execution for Workspace A
    exec_a = PlatformExecutionResult(
        execution_id="exec_a1",
        capability_id="knowledge.rag",
        status=LifecycleState.COMPLETED,
        output={"answer": "ok"},
        provenance=[
            ProvenanceItem(
                source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
                source_id="chunk_1",
                workspace_id=ws_a,
                trust_level=ProvenanceTrustLevel.VERIFIED_RAG
            )
        ],
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=150),
        duration_ms=150.0,
        correlation_id="corr_a1",
        metadata={"workspace_id": str(ws_a)}
    )

    exec_b = PlatformExecutionResult(
        execution_id="exec_b1",
        capability_id="mcp.tool",
        status=LifecycleState.FAILED,
        output={},
        errors=[{"code": "MCP_ERROR", "message": "Failed token secret_tok_123"}],
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=300),
        duration_ms=300.0,
        correlation_id="corr_b1",
        metadata={"workspace_id": str(ws_b)}
    )

    PlatformExecutionService._executions[exec_a.execution_id] = exec_a
    PlatformExecutionService._executions[exec_b.execution_id] = exec_b

    obs_service = PlatformObservabilityService(db_session)
    
    # Workspace A Overview
    metrics_a = obs_service.get_overview_metrics(ws_a, time_window="24h")
    assert metrics_a.total_executions >= 1
    assert metrics_a.successful_executions >= 1
    assert metrics_a.failed_executions == 0
    assert metrics_a.success_rate == 100.0
    assert "knowledge.rag" in metrics_a.executions_per_capability

    # Workspace B Overview
    metrics_b = obs_service.get_overview_metrics(ws_b, time_window="24h")
    assert metrics_b.total_executions >= 1
    assert metrics_b.successful_executions == 0
    assert metrics_b.failed_executions >= 1
    assert metrics_b.failure_rate == 100.0
    assert "mcp.tool" in metrics_b.executions_per_capability

def test_capability_performance_and_health_classification(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    # 3 successful executions for knowledge.rag
    for i in range(3):
        ex = PlatformExecutionResult(
            execution_id=f"exec_rag_{i}",
            capability_id="knowledge.rag",
            status=LifecycleState.COMPLETED,
            started_at=now,
            completed_at=now + datetime.timedelta(milliseconds=200),
            duration_ms=200.0,
            correlation_id=f"corr_rag_{i}",
            metadata={"workspace_id": str(ws_a)}
        )
        PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    res = obs_service.get_capability_performance(ws_a, time_window="24h")

    rag_metric = next((m for m in res.items if m.capability_id == "knowledge.rag"), None)
    assert rag_metric is not None
    assert rag_metric.execution_count >= 3
    assert rag_metric.success_rate == 100.0
    assert rag_metric.health == CapabilityHealth.HEALTHY

def test_provenance_analytics_and_trust_distribution(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    ex = PlatformExecutionResult(
        execution_id="exec_prov_1",
        capability_id="agent.orchestrator",
        status=LifecycleState.COMPLETED,
        provenance=[
            ProvenanceItem(
                source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
                source_id="c1",
                title="Policy Document",
                workspace_id=ws_a,
                trust_level=ProvenanceTrustLevel.VERIFIED_RAG
            ),
            ProvenanceItem(
                source_type=ProvenanceSourceType.GRAPH_NODE,
                source_id="n1",
                title="Entity Alpha",
                workspace_id=ws_a,
                trust_level=ProvenanceTrustLevel.VERIFIED_GRAPH
            )
        ],
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=500),
        duration_ms=500.0,
        correlation_id="corr_prov_1",
        metadata={"workspace_id": str(ws_a)}
    )
    PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    prov_res = obs_service.get_provenance_analytics(ws_a, time_window="24h")

    assert prov_res.total_evidence_items >= 2
    assert prov_res.source_distribution.get("document_chunk", 0) >= 1
    assert prov_res.trust_distribution.get("verified_rag", 0) >= 1

def test_failure_analytics_and_secret_redaction(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    ex = PlatformExecutionResult(
        execution_id="exec_fail_1",
        capability_id="mcp.tool",
        status=LifecycleState.FAILED,
        errors=[{"code": "TIMEOUT", "message": "Connection timeout for user token Authorization: Bearer secret-tok-999"}],
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=1000),
        duration_ms=1000.0,
        correlation_id="corr_fail_1",
        metadata={"workspace_id": str(ws_a)}
    )
    PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    fail_res = obs_service.get_failure_analytics(ws_a, time_window="24h")

    assert fail_res.total_failures >= 1
    assert len(fail_res.recent_failures) >= 1
    recent = fail_res.recent_failures[0]
    assert "[REDACTED]" in recent.normalized_message
    assert "secret-tok-999" not in recent.normalized_message

def test_execution_timeline_and_tenant_isolation(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    ws_b = obs_setup["ws_b"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    ex = PlatformExecutionResult(
        execution_id="exec_timeline_1",
        capability_id="workflow.engine",
        status=LifecycleState.COMPLETED,
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=800),
        duration_ms=800.0,
        correlation_id="corr_tl_1",
        metadata={"workspace_id": str(ws_a)}
    )
    PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    
    # Authorized workspace retrieval
    timeline_a = obs_service.get_execution_timeline(ex.execution_id, ws_a)
    assert timeline_a is not None
    assert timeline_a.execution_id == ex.execution_id
    assert len(timeline_a.events) >= 2

    # Unauthorized workspace denial
    timeline_b = obs_service.get_execution_timeline(ex.execution_id, ws_b)
    assert timeline_b is None

def test_lifecycle_and_bottleneck_detection(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    # Seed 3 slow executions for knowledge.graph
    for i in range(3):
        ex = PlatformExecutionResult(
            execution_id=f"exec_graph_{i}",
            capability_id="knowledge.graph",
            status=LifecycleState.COMPLETED,
            started_at=now,
            completed_at=now + datetime.timedelta(milliseconds=20000),
            duration_ms=20000.0,
            correlation_id=f"corr_graph_{i}",
            metadata={"workspace_id": str(ws_a)}
        )
        PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    
    lifecycle = obs_service.get_lifecycle_metrics(ws_a, time_window="24h")
    assert "completed" in lifecycle.status_distribution or "COMPLETED" in lifecycle.status_distribution
    assert "EXECUTING" in lifecycle.stage_durations_ms

    bottlenecks = obs_service.get_bottleneck_analytics(ws_a, time_window="24h")
    assert len(bottlenecks.bottlenecks) >= 1
    slow_b = next((b for b in bottlenecks.bottlenecks if b.capability_id == "knowledge.graph"), None)
    assert slow_b is not None
    assert slow_b.classification == BottleneckClassification.SLOW_EXECUTION

def test_intelligence_analytics_metrics(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    ex = PlatformExecutionResult(
        execution_id="exec_intel_obs_1",
        capability_id="intelligence.orchestrator",
        status=LifecycleState.COMPLETED,
        output={
            "mode": "adaptive",
            "confidence": 0.95,
            "confidence_level": "HIGH",
            "plan": {
                "steps": [
                    {"step_id": "s1", "requirement_type": "document_evidence"},
                    {"step_id": "s2", "requirement_type": "graph_reasoning"}
                ]
            },
            "decisions": [
                {"decision_type": "continue"},
                {"decision_type": "complete"}
            ]
        },
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=1200),
        duration_ms=1200.0,
        correlation_id="corr_intel_1",
        metadata={"workspace_id": str(ws_a)}
    )
    PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    intel = obs_service.get_intelligence_analytics(ws_a, time_window="24h")

    assert intel.avg_confidence >= 0.90
    assert intel.high_confidence_count >= 1
    assert "adaptive" in intel.execution_mode_distribution
    assert "document_evidence" in intel.requirement_distribution

def test_alert_evaluation_rules(db_session: Session, obs_setup):
    ws_a = obs_setup["ws_a"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    # Seed 5 consecutive failures for capability mcp.tool
    for i in range(5):
        ex = PlatformExecutionResult(
            execution_id=f"exec_alert_{i}",
            capability_id="mcp.tool",
            status=LifecycleState.FAILED,
            errors=[{"code": "FAILED", "message": "Failed service"}],
            started_at=now,
            completed_at=now + datetime.timedelta(milliseconds=30000),
            duration_ms=30000.0,
            correlation_id=f"corr_alert_{i}",
            metadata={"workspace_id": str(ws_a)}
        )
        PlatformExecutionService._executions[ex.execution_id] = ex

    obs_service = PlatformObservabilityService(db_session)
    alerts_res = obs_service.get_alerts(ws_a, time_window="24h")

    assert alerts_res.total_alerts >= 1
    alert_types = [a.alert_type for a in alerts_res.alerts]
    assert "HIGH_FAILURE_RATE" in alert_types or "CAPABILITY_UNAVAILABLE" in alert_types
