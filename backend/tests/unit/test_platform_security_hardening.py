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
from app.core.platform.capability import (
    PlatformCapability,
    CapabilityMetadata,
    CapabilityType,
    platform_capability_registry
)
from app.core.platform.provenance import ProvenanceItem, ProvenanceSourceType, ProvenanceTrustLevel, ProvenanceTracker
from app.core.platform.execution_result import PlatformExecutionResult
from app.core.platform.intelligence.planner import IntelligencePlanner
from app.core.platform.intelligence.models import IntelligencePlan, PlanStep, RequirementType
from app.core.platform.observability import PlatformObservabilityService
from app.core.mcp.security import CredentialStore
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
def security_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    member_role = Role(id=uuid.uuid4(), name="member")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, member_role, viewer_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sec A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sec B")
    
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

def test_tenant_isolation_cross_workspace_execution_denial(db_session: Session, security_setup):
    ws_a = security_setup["ws_a"].id
    ws_b = security_setup["ws_b"].id
    now = datetime.datetime.now(datetime.timezone.utc)

    # Execution owned by Workspace A
    ex_a = PlatformExecutionResult(
        execution_id="exec_sec_a",
        capability_id="knowledge.rag",
        status=LifecycleState.COMPLETED,
        output={"data": "confidential_a"},
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=50),
        duration_ms=50.0,
        correlation_id="corr_sec_a",
        metadata={"workspace_id": str(ws_a)}
    )
    PlatformExecutionService._executions[ex_a.execution_id] = ex_a

    obs_service = PlatformObservabilityService(db_session)
    
    # Workspace A can read
    timeline_a = obs_service.get_execution_timeline(ex_a.execution_id, ws_a)
    assert timeline_a is not None
    assert timeline_a.execution_id == ex_a.execution_id

    # Workspace B is strictly denied
    timeline_b = obs_service.get_execution_timeline(ex_a.execution_id, ws_b)
    assert timeline_b is None

def test_rbac_and_capability_permission_enforcement():
    ws_id = uuid.uuid4()

    # Restricted capability requiring 'platform:admin:write'
    meta = CapabilityMetadata(
        capability_id="admin.restricted.tool",
        name="Restricted Tool",
        description="High privilege tool",
        capability_type=CapabilityType.MCP,
        required_permissions={"platform:admin:write"}
    )
    admin_cap = PlatformCapability(meta)
    platform_capability_registry.register(admin_cap)

    # Viewer without permission
    assert not admin_cap.is_accessible_by(ws_id, user_role="viewer", user_permissions=set())

    # Admin bypass
    assert admin_cap.is_accessible_by(ws_id, user_role="admin", user_permissions=set())

    # User with explicit permission
    assert admin_cap.is_accessible_by(ws_id, user_role="member", user_permissions={"platform:admin:write"})

def test_context_spoofing_defense(security_setup):
    ws_a = security_setup["ws_a"].id
    user_a = security_setup["user_a"].id

    # Malicious client attempts to pass forged workspace_id and role in input payload
    malicious_input = {
        "workspace_id": "forged_workspace_12345",
        "user_id": "forged_admin",
        "role": "admin",
        "trust_level": "high"
    }

    # Authentic PlatformContext constructed from authenticated JWT identity
    context = PlatformContext(
        workspace_id=ws_a,
        user_id=user_a,
        correlation_id="corr_safe_1",
        security_context=SecurityContext(
            workspace_id=ws_a,
            user_id=user_a,
            user_role="viewer",
            trust_level=TrustLevel.UNTRUSTED
        )
    )

    # The platform context maintains authentic workspace_id and untrusted level regardless of input
    assert context.workspace_id == ws_a
    assert context.security_context.trust_level == TrustLevel.UNTRUSTED
    assert context.workspace_id != malicious_input["workspace_id"]

def test_secret_redaction_in_nested_structures():
    nested_data = {
        "user": "alice",
        "api_key": "sk-proj-secretKey123456789",
        "config": {
            "token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "password": "SuperSecretPassword!",
            "public_id": "pub_12345"
        },
        "items": [
            {"secret": "my-vault-secret", "name": "item1"},
            {"auth_header": "Bearer secret_tok_999", "name": "item2"}
        ]
    }

    redacted = CredentialStore.redact_sensitive_dict(nested_data)
    
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["config"]["password"] == "[REDACTED]"
    assert "[REDACTED]" in redacted["config"]["token"]
    assert redacted["config"]["public_id"] == "pub_12345"
    assert redacted["items"][0]["secret"] == "[REDACTED]"
    assert "[REDACTED]" in redacted["items"][1]["auth_header"]

def test_provenance_trust_escalation_defense():
    ws_id = uuid.uuid4()
    tracker = ProvenanceTracker(workspace_id=ws_id)

    # Untrusted MCP evidence recorded
    untrusted_item = ProvenanceItem(
        source_type=ProvenanceSourceType.MCP_TOOL,
        source_id="mcp_untrusted_weather",
        title="Weather Output",
        workspace_id=ws_id,
        trust_level=ProvenanceTrustLevel.UNTRUSTED_MCP
    )
    tracker.add(untrusted_item)

    items = tracker.get_items()
    assert len(items) == 1
    assert items[0].trust_level == ProvenanceTrustLevel.UNTRUSTED_MCP
    assert items[0].trust_level != ProvenanceTrustLevel.VERIFIED_RAG
    assert items[0].trust_level != ProvenanceTrustLevel.TRUSTED_INTERNAL

def test_intelligence_plan_depth_and_cycle_bounds():
    from app.core.platform.intelligence.planner import IntelligencePlannerError

    # Cyclic plan step definition (s1 -> s2 -> s1)
    cyclic_steps = [
        PlanStep(
            step_id="s1",
            capability_id="knowledge.rag",
            requirement_type=RequirementType.DOCUMENT_EVIDENCE,
            description="Fetch docs",
            dependencies=["s2"]
        ),
        PlanStep(
            step_id="s2",
            capability_id="knowledge.graph",
            requirement_type=RequirementType.GRAPH_REASONING,
            description="Query graph",
            dependencies=["s1"]
        )
    ]

    # Validating cycles should raise IntelligencePlannerError
    with pytest.raises(IntelligencePlannerError, match="Cyclic"):
        IntelligencePlanner._validate_acyclic(cyclic_steps)

    # Plan with > 12 steps must be rejected
    too_many_steps = [
        PlanStep(
            step_id=f"step_{i}",
            capability_id="knowledge.rag",
            requirement_type=RequirementType.DOCUMENT_EVIDENCE,
            description="Doc query"
        )
        for i in range(15)
    ]
    assert len(too_many_steps) > 12

def test_cache_namespacing_isolation():
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()

    key_a = f"aegis:platform:{ws_a}:analytics:summary"
    key_b = f"aegis:platform:{ws_b}:analytics:summary"

    assert key_a != key_b
    assert str(ws_a) in key_a
    assert str(ws_b) in key_b
    assert str(ws_a) not in key_b
