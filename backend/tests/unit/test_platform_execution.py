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
from app.core.platform.capability import (
    CapabilityMetadata,
    CapabilityType,
    PlatformCapability,
    platform_capability_registry
)
from app.core.platform.adapter import (
    BaseCapabilityExecutor,
    platform_dispatcher
)
from app.services.platform_execution import PlatformExecutionService
from app.core.platform.events import PlatformEventDispatcher, PlatformEventType

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def exec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Exec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Exec")
    user = User(
        id=uuid.uuid4(),
        email="exec_user@test.com",
        username="exec_user",
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

def test_successful_execution_and_lifecycle(db_session: Session, exec_setup):
    ws = exec_setup["ws"]
    user = exec_setup["user"]

    sec_ctx = SecurityContext(
        user_id=user.id,
        workspace_id=ws.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user.id,
        workspace_id=ws.id,
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)

    # Execute echo capability
    res = service.execute(
        capability_id="echo.test",
        context=context,
        input_data={"message": "Hello Execution Engine"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert res.output["echo"]["message"] == "Hello Execution Engine"
    assert len(res.provenance) >= 1
    assert res.duration_ms > 0
    assert len(res.errors) == 0

def test_execution_adapters_suite(db_session: Session, exec_setup):
    """Test standard adapters (agent, rag, graph, memory, mcp, workflow)."""
    ws = exec_setup["ws"]
    user = exec_setup["user"]
    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    # 1. RAG
    rag_res = service.execute("rag.retriever", context, {"query": "What is AegisAI?"})
    assert rag_res.status == LifecycleState.COMPLETED
    assert "Retrieved knowledge" in rag_res.output["chunks"][0]["text"]

    # 2. Agent
    agent_res = service.execute("agent.orchestrator", context, {"prompt": "Plan task"})
    assert agent_res.status == LifecycleState.COMPLETED
    assert "response" in agent_res.output

    # 3. Graph
    graph_res = service.execute("knowledge_graph.engine", context, {"entity": "AI Platform"})
    assert graph_res.status == LifecycleState.COMPLETED
    assert graph_res.output["nodes_found"] == 1

    # 4. Memory
    mem_res = service.execute("memory.manager", context, {"key": "user_pref"})
    assert mem_res.status == LifecycleState.COMPLETED
    assert len(mem_res.output["facts"]) >= 1

    # 5. MCP
    mcp_res = service.execute("mcp.platform", context, {"tool_name": "fetch_data"})
    assert mcp_res.status == LifecycleState.COMPLETED
    assert mcp_res.output["tool"] == "fetch_data"

    # 6. Workflow
    wf_res = service.execute("workflow.engine", context, {"workflow_id": "wf_123"})
    assert wf_res.status == LifecycleState.COMPLETED
    assert wf_res.output["execution_status"] == "COMPLETED"

def test_missing_and_disabled_capability(db_session: Session, exec_setup):
    ws = exec_setup["ws"]
    user = exec_setup["user"]
    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    # 1. Missing capability
    res_missing = service.execute("unknown.cap", context, {})
    assert res_missing.status == LifecycleState.FAILED
    assert "CAPABILITY_NOT_FOUND" in res_missing.errors[0]["code"]

    # 2. Disabled capability
    disabled_meta = CapabilityMetadata(
        capability_id="disabled.cap",
        capability_type=CapabilityType.REASONING,
        name="Disabled Tool",
        description="Offline tool",
        enabled=False
    )
    class DummyCap(PlatformCapability):
        pass
    platform_capability_registry.register(DummyCap(disabled_meta))

    res_disabled = service.execute("disabled.cap", context, {})
    assert res_disabled.status == LifecycleState.FAILED
    assert "CAPABILITY_DISABLED" in res_disabled.errors[0]["code"]

def test_idempotency_and_cancellation(db_session: Session, exec_setup):
    ws = exec_setup["ws"]
    user = exec_setup["user"]
    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    # 1. Idempotency
    r1 = service.execute("echo.test", context, {"data": "idempotent_test"}, idempotency_key="key_123")
    r2 = service.execute("echo.test", context, {"data": "idempotent_test"}, idempotency_key="key_123")
    assert r1.execution_id == r2.execution_id

    # 2. Cancellation
    cancel_res = service.cancel_execution(r1.execution_id, user.id, ws.id, reason="User cancelled execution")
    assert cancel_res is not None
    assert cancel_res.status == LifecycleState.CANCELLED

def test_secret_redaction_in_execution_result(db_session: Session, exec_setup):
    ws = exec_setup["ws"]
    user = exec_setup["user"]
    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        "echo.test",
        context,
        {
            "user": "Alice",
            "api_key": "sk-1234567890abcdef",
            "password": "SuperSecretPassword123!"
        }
    )

    safe_dict = res.to_safe_dict()
    assert safe_dict["output"]["echo"]["user"] == "Alice"
    assert safe_dict["output"]["echo"]["api_key"] == "[REDACTED]"
    assert safe_dict["output"]["echo"]["password"] == "[REDACTED]"
