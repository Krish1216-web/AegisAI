import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.provenance import ProvenanceTrustLevel
from app.core.platform.intelligence.models import ExecutionMode, AdaptiveDecisionType
from app.core.platform.intelligence.engine import AdvancedIntelligenceService
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
def intel_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Intel Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Intel")
    user = User(
        id=uuid.uuid4(),
        email="intel_user@test.com",
        username="intel_user",
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

def test_intelligent_query_full_execution(db_session: Session, intel_setup):
    ws = intel_setup["ws"]
    user = intel_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = AdvancedIntelligenceService(db_session)
    res = service.execute_intelligent_query(
        query="Retrieve company security policy documents and resolve related system entities",
        context=context,
        mode=ExecutionMode.ADAPTIVE
    )

    assert res["status"].upper() == "COMPLETED"
    assert len(res["plan"]["steps"]) >= 2
    assert len(res["decisions"]) >= 2
    assert res["confidence"] > 0.0
    assert len(res["provenance"]) >= 1
    assert "response" in res["output"]

def test_intelligent_capability_via_platform_dispatcher(db_session: Session, intel_setup):
    ws = intel_setup["ws"]
    user = intel_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    exec_service = PlatformExecutionService(db_session)
    res = exec_service.execute(
        capability_id="intelligence.orchestrator",
        context=context,
        input_data={"query": "Synthesize intelligence report on active platform capabilities", "mode": "sequential"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert "plan" in res.output
    assert "decisions" in res.output

def test_intelligent_mcp_confirmation_waiting_gating(db_session: Session, intel_setup):
    ws = intel_setup["ws"]
    user = intel_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = AdvancedIntelligenceService(db_session)
    res = service.execute_intelligent_query(
        query="Execute database tool to delete production records via MCP",
        context=context,
        input_data={"tool_name": "delete_records", "risk_level": "RESTRICTED"}
    )

    assert res["status"].upper() == "WAITING"
    assert res["output"]["confirmation_info"] is not None
    assert "token" in str(res["output"]["confirmation_info"]) or "confirmation_token" in str(res["output"]["confirmation_info"])

def test_intelligent_cross_tenant_denial(db_session: Session, intel_setup):
    user = intel_setup["user"]
    ws_a = intel_setup["ws"]
    ws_b = uuid.uuid4() # Non-matching workspace

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws_a.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws_b, security_context=sec_ctx)

    exec_service = PlatformExecutionService(db_session)
    res = exec_service.execute(
        capability_id="intelligence.orchestrator",
        context=context,
        input_data={"query": "Search documents"}
    )

    assert res.status == LifecycleState.DENIED
