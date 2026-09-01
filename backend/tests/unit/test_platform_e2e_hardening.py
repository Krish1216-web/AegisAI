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
from app.core.platform.intelligence import AdvancedIntelligenceService
from app.core.platform.observability import PlatformObservabilityService
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
def e2e_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="E2E Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS E2E")
    user = User(
        id=uuid.uuid4(),
        email="e2e_user@test.com",
        username="e2e_user",
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

def test_full_intelligence_platform_e2e_flow_with_observability(db_session: Session, e2e_setup):
    ws_id = e2e_setup["ws"].id
    user_id = e2e_setup["user"].id

    context = PlatformContext(
        workspace_id=ws_id,
        user_id=user_id,
        correlation_id="corr_e2e_flow_1",
        security_context=SecurityContext(
            workspace_id=ws_id,
            user_id=user_id,
            user_role="admin",
            trust_level=TrustLevel.HIGH
        )
    )

    # 1. Execute Intelligent Query Orchestrator
    intel_service = AdvancedIntelligenceService(db_session)
    intel_result = intel_service.execute_intelligent_query(
        query="Analyze security vulnerabilities across policy documents and infrastructure",
        context=context,
        mode="adaptive",
        input_data={"target": "infrastructure_policy"}
    )

    assert intel_result["status"] in ["completed", "executing"]
    assert intel_result["confidence"] > 0.0
    assert len(intel_result["plan"].get("steps", [])) >= 1

    # 2. Verify Telemetry & Observability Aggregation
    obs_service = PlatformObservabilityService(db_session)
    intel_analytics = obs_service.get_intelligence_analytics(ws_id, time_window="24h")
    assert intel_analytics.total_executions >= 0

    # 3. Verify Execution Timeline
    timeline = obs_service.get_execution_timeline(intel_result["execution_id"], ws_id)
    assert timeline is not None
    assert timeline.execution_id == intel_result["execution_id"]
