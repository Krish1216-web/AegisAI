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
from app.core.platform.capability import CapabilityType, platform_capability_registry
from app.core.platform.mcp_bridge import MCPContextBridge
from app.core.platform.provenance import ProvenanceSourceType, ProvenanceTrustLevel
from app.core.platform.events import PlatformEventType, PlatformEvent, PlatformEventDispatcher
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
def mcp_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="MCP Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS MCP")
    user = User(
        id=uuid.uuid4(),
        email="mcp_user@test.com",
        username="mcp_user",
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

def test_mcp_context_bridge_tool_params(mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    input_data = {
        "tool_name": "query_database",
        "arguments": {"sql": "SELECT * FROM users", "api_key": "secret_key_12345"},
        "workspace_id": str(uuid.uuid4()) # Malicious override attempt
    }

    params = MCPContextBridge.platform_context_to_tool_params(context, input_data)

    assert params["tool_name"] == "query_database"
    assert params["workspace_id"] == ws.id # Locked
    assert params["user_id"] == user.id # Locked
    assert params["arguments"]["api_key"] == "[REDACTED]"

def test_mcp_context_bridge_resource_and_prompt(mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    # 1. Resource Result Transformation
    res_data = {
        "uri": "https://api.github.com/repos/org/repo/readme",
        "content": "Repository documentation and instructions.",
        "server_id": "srv_github"
    }
    r_out, r_prov = MCPContextBridge.resource_result_to_execution_output(res_data, context, {"resource_id": "res_1"})
    assert r_out["resource_uri"] == "https://api.github.com/repos/org/repo/readme"
    assert len(r_prov) == 1
    assert r_prov[0].source_type == ProvenanceSourceType.MCP_RESOURCE
    assert r_prov[0].trust_level == ProvenanceTrustLevel.UNTRUSTED_MCP

    # 2. Prompt Result Transformation
    prompt_data = {
        "prompt_name": "code_review",
        "server_id": "srv_dev",
        "messages": [{"role": "user", "content": "Review this diff"}]
    }
    p_out, p_prov = MCPContextBridge.prompt_result_to_execution_output(prompt_data, context, {"prompt_id": "p_1"})
    assert p_out["prompt_name"] == "code_review"
    assert len(p_prov) == 1
    assert p_prov[0].source_type == ProvenanceSourceType.MCP_PROMPT
    assert p_prov[0].trust_level == ProvenanceTrustLevel.UNTRUSTED_MCP

def test_platform_mcp_tool_execution(db_session: Session, mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="mcp.tool",
        context=context,
        input_data={"tool_name": "calculator", "arguments": {"expr": "2 + 2"}}
    )

    assert res.status == LifecycleState.COMPLETED
    assert res.output["tool_name"] == "calculator"
    assert len(res.provenance) >= 1
    assert res.provenance[0].trust_level == ProvenanceTrustLevel.UNTRUSTED_MCP

def test_platform_mcp_tool_restricted_confirmation(db_session: Session, mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="mcp.tool",
        context=context,
        input_data={
            "tool_name": "delete_database",
            "risk_level": "RESTRICTED",
            "arguments": {"target": "prod_db"}
        }
    )

    assert res.status == LifecycleState.COMPLETED
    assert res.output["status"] == "WAITING"
    assert res.output["confirmation_required"] is True
    assert "confirmation_token" in res.output

def test_platform_mcp_resource_execution(db_session: Session, mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="mcp.resource",
        context=context,
        input_data={"uri": "https://api.example.com/data.json"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert res.output["resource_uri"] == "https://api.example.com/data.json"
    assert len(res.provenance) >= 1
    assert res.provenance[0].trust_level == ProvenanceTrustLevel.UNTRUSTED_MCP

def test_platform_mcp_prompt_execution(db_session: Session, mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="mcp.prompt",
        context=context,
        input_data={"prompt_name": "system_diagnostics", "arguments": {"subsystem": "auth"}}
    )

    assert res.status == LifecycleState.COMPLETED
    assert res.output["prompt_name"] == "system_diagnostics"
    assert len(res.provenance) >= 1
    assert res.provenance[0].trust_level == ProvenanceTrustLevel.UNTRUSTED_MCP

def test_platform_mcp_events(db_session: Session, mcp_setup):
    ws = mcp_setup["ws"]
    user = mcp_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    captured_events = []
    def event_listener(evt: PlatformEvent):
        captured_events.append(evt)

    PlatformEventDispatcher.subscribe(PlatformEventType.MCP_EVENT, event_listener)

    service = PlatformExecutionService(db_session)
    res = service.execute("mcp.tool", context, {"tool_name": "ping_service"})

    assert res.status == LifecycleState.COMPLETED
    assert len(captured_events) >= 1
    actions = [e.payload.get("action") for e in captured_events]
    assert "mcp_tool_started" in actions
