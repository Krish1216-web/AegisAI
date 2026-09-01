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
from app.core.platform.mcp_bridge import MCPContextBridge
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
def mcp_sec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="MCP Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, viewer_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS MCP A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS MCP B")
    user_a = User(
        id=uuid.uuid4(),
        email="mcp_a@test.com",
        username="mcp_a",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user_b = User(
        id=uuid.uuid4(),
        email="mcp_b@test.com",
        username="mcp_b",
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

def test_cross_tenant_mcp_tool_denial(db_session: Session, mcp_sec_setup):
    user_a = mcp_sec_setup["user_a"]
    ws_a = mcp_sec_setup["ws_a"]
    ws_b = mcp_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_b.id, # Cross-tenant attempt
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("mcp.tool", context, {"tool_name": "execute_shell"})

    assert res.status == LifecycleState.DENIED
    assert len(res.errors) >= 1
    assert "Cross-tenant" in res.errors[0]["message"]

def test_cross_tenant_mcp_resource_denial(db_session: Session, mcp_sec_setup):
    user_a = mcp_sec_setup["user_a"]
    ws_a = mcp_sec_setup["ws_a"]
    ws_b = mcp_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_b.id,
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("mcp.resource", context, {"uri": "https://api.github.com/secret"})

    assert res.status == LifecycleState.DENIED

def test_mcp_input_spoofing_defense(mcp_sec_setup):
    user_a = mcp_sec_setup["user_a"]
    ws_a = mcp_sec_setup["ws_a"]
    ws_b = mcp_sec_setup["ws_b"]

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

    malicious_input = {
        "tool_name": "transfer_funds",
        "workspace_id": str(ws_b.id),
        "user_id": str(uuid.uuid4())
    }

    params = MCPContextBridge.platform_context_to_tool_params(context, malicious_input)

    assert params["workspace_id"] == ws_a.id
    assert params["workspace_id"] != ws_b.id
    assert params["user_id"] == user_a.id

def test_mcp_ssrf_forbidden_uri_rejection(db_session: Session, mcp_sec_setup):
    user_a = mcp_sec_setup["user_a"]
    ws_a = mcp_sec_setup["ws_a"]

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

    service = PlatformExecutionService(db_session)

    # 1. file:// uri forbidden
    res = service.execute("mcp.resource", context, {"uri": "file:///etc/passwd"})
    assert res.status == LifecycleState.FAILED
    assert "INVALID_EXECUTION_INPUT" in res.errors[0]["code"]

    # 2. localhost uri forbidden
    res_loc = service.execute("mcp.resource", context, {"uri": "http://localhost:8080/admin"})
    assert res_loc.status == LifecycleState.FAILED
    assert "INVALID_EXECUTION_INPUT" in res_loc.errors[0]["code"]

def test_mcp_credential_redaction(db_session: Session, mcp_sec_setup):
    user_a = mcp_sec_setup["user_a"]
    ws_a = mcp_sec_setup["ws_a"]

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

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="mcp.tool",
        context=context,
        input_data={
            "tool_name": "sync_crm",
            "arguments": {
                "token": "sk-live-secret-abcdef",
                "auth_header": "Bearer secret-token-xyz"
            }
        }
    )

    assert res.status == LifecycleState.COMPLETED
    out_str = str(res.output)
    assert "sk-live-secret-abcdef" not in out_str
    assert "[REDACTED]" in out_str
