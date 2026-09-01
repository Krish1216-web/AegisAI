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
from app.core.platform.agent_bridge import AgentContextBridge
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
def agent_sec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Agent Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, viewer_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Agent A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Agent B")
    user_a = User(
        id=uuid.uuid4(),
        email="ua@test.com",
        username="ua",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user_b = User(
        id=uuid.uuid4(),
        email="ub@test.com",
        username="ub",
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

def test_cross_tenant_agent_execution_denial(db_session: Session, agent_sec_setup):
    user_a = agent_sec_setup["user_a"]
    ws_a = agent_sec_setup["ws_a"]
    ws_b = agent_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id, # Caller belongs to WS A
        user_role="admin"
    )
    # Context targets WS B illegally
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_b.id,
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("agent.orchestrator", context, {"query": "Extract classified data"})

    assert res.status == LifecycleState.DENIED
    assert len(res.errors) >= 1
    assert "Cross-tenant" in res.errors[0]["message"]

def test_context_spoofing_defense(agent_sec_setup):
    user_a = agent_sec_setup["user_a"]
    ws_a = agent_sec_setup["ws_a"]
    ws_b = agent_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        security_context=sec_ctx
    )

    # Malicious payload trying to override workspace_id and user_id
    malicious_input = {
        "query": "List all records",
        "workspace_id": str(ws_b.id),
        "user_id": str(uuid.uuid4()),
        "security_context": {"user_role": "super_admin"}
    }

    state = AgentContextBridge.platform_context_to_agent_state(context, malicious_input)

    # Bridge MUST reject input override and preserve context identity
    assert state["workspace_id"] == str(ws_a.id)
    assert state["user_id"] == str(user_a.id)
    assert state["workspace_id"] != str(ws_b.id)
