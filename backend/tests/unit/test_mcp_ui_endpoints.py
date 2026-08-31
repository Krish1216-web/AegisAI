import pytest
import uuid
import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, WorkspaceMember, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPServerStatus, MCPCapabilityType, MCPTransport, MCPAuthenticationType
from app.models.ai import Execution, ToolExecution
from app.services.mcp.mcp_security import MCPSecurityService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_setup(db_session: Session):
    # Setup Workspace 1
    org1 = Organization(id=uuid.uuid4(), name="Org 1")
    role1 = Role(id=uuid.uuid4(), name="Admin")
    db_session.add_all([org1, role1])
    db_session.flush()

    ws1 = Workspace(id=uuid.uuid4(), organization_id=org1.id, name="MCP UI Workspace 1")
    user1 = User(id=uuid.uuid4(), email=f"mcp_ui_user1_{uuid.uuid4().hex[:6]}@test.com", username=f"user1_{uuid.uuid4().hex[:6]}", password_hash="hash", role_id=role1.id, is_active=True)
    db_session.add_all([ws1, user1])
    db_session.flush()

    member1 = WorkspaceMember(workspace_id=ws1.id, user_id=user1.id, role="admin")
    db_session.add(member1)

    # Server 1 in WS 1
    server1 = MCPServer(
        id=uuid.uuid4(),
        workspace_id=ws1.id,
        user_id=user1.id,
        name="server-ws1",
        server_url="http://localhost:8001/sse",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True,
        authentication_type=MCPAuthenticationType.NONE,
        last_discovery_at=datetime.datetime.now(datetime.timezone.utc),
        last_health_check_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(server1)
    db_session.flush()

    # Capabilities in WS 1
    tool1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="tool_ws1",
        description="Tool in WS 1",
        input_schema={"type": "object"},
        enabled=True,
        is_stale=False
    )
    res1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="resource_ws1",
        description="Resource in WS 1",
        input_schema={"uri": "workspace://ws1/doc.md"},
        enabled=True,
        is_stale=False
    )
    prm1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server1.id,
        capability_type=MCPCapabilityType.PROMPT,
        name="prompt_ws1",
        description="Prompt in WS 1",
        input_schema={},
        enabled=True,
        is_stale=False
    )
    db_session.add_all([tool1, res1, prm1])
    db_session.flush()

    # Execution & Tool Execution in WS 1
    exec1 = Execution(
        id=uuid.uuid4(),
        user_id=user1.id,
        workspace_id=ws1.id,
        status="COMPLETED",
        original_request="Test MCP Execution in WS1"
    )
    db_session.add(exec1)
    db_session.flush()

    te1 = ToolExecution(
        id=uuid.uuid4(),
        execution_id=exec1.id,
        tool_id=str(tool1.id),
        status="COMPLETED",
        arguments_hash="hash1",
        started_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1),
        completed_at=datetime.datetime.now(datetime.timezone.utc),
        result=json.dumps({"status": "SUCCESS", "token": "sensitive_secret_token", "data": "clean_result"})
    )
    db_session.add(te1)

    # Setup Workspace 2
    org2 = Organization(id=uuid.uuid4(), name="Org 2")
    db_session.add(org2)
    db_session.flush()

    ws2 = Workspace(id=uuid.uuid4(), organization_id=org2.id, name="MCP UI Workspace 2")
    user2 = User(id=uuid.uuid4(), email=f"mcp_ui_user2_{uuid.uuid4().hex[:6]}@test.com", username=f"user2_{uuid.uuid4().hex[:6]}", password_hash="hash", role_id=role1.id, is_active=True)
    db_session.add_all([ws2, user2])
    db_session.flush()

    member2 = WorkspaceMember(workspace_id=ws2.id, user_id=user2.id, role="admin")
    db_session.add(member2)

    server2 = MCPServer(
        id=uuid.uuid4(),
        workspace_id=ws2.id,
        user_id=user2.id,
        name="server-ws2",
        server_url="http://localhost:8002/sse",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True,
        authentication_type=MCPAuthenticationType.NONE
    )
    db_session.add(server2)
    db_session.flush()

    tool2 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server2.id,
        capability_type=MCPCapabilityType.TOOL,
        name="tool_ws2",
        description="Tool in WS 2",
        input_schema={"type": "object"},
        enabled=True,
        is_stale=False
    )
    db_session.add(tool2)
    db_session.commit()

    return {
        "user1": user1,
        "ws1": ws1,
        "server1": server1,
        "tool1": tool1,
        "res1": res1,
        "prm1": prm1,
        "exec1": exec1,
        "te1": te1,
        "user2": user2,
        "ws2": ws2,
        "server2": server2,
        "tool2": tool2
    }

def test_mcp_overview_metrics_tenant_isolation(db_session: Session, test_setup):
    from app.api.v1.endpoints.mcp import get_mcp_overview_metrics

    # Query for User 1 in WS 1
    metrics1 = get_mcp_overview_metrics(current_user=test_setup["user1"], db=db_session)
    assert metrics1.servers.total == 1
    assert metrics1.servers.active == 1
    assert metrics1.capabilities.total_tools == 1
    assert metrics1.capabilities.total_resources == 1
    assert metrics1.capabilities.total_prompts == 1
    assert metrics1.capabilities.enabled_capabilities == 3
    assert metrics1.execution.total >= 1
    assert metrics1.health.healthy_servers == 1

    # Query for User 2 in WS 2
    metrics2 = get_mcp_overview_metrics(current_user=test_setup["user2"], db=db_session)
    assert metrics2.servers.total == 1
    assert metrics2.capabilities.total_tools == 1
    assert metrics2.capabilities.total_resources == 0
    assert metrics2.capabilities.total_prompts == 0
    assert metrics2.execution.total == 0

def test_mcp_execution_history_tenant_isolation_and_sanitization(db_session: Session, test_setup):
    from app.api.v1.endpoints.mcp import get_mcp_execution_history

    # Query for User 1
    hist1 = get_mcp_execution_history(
        status_filter=None,
        limit=50,
        offset=0,
        current_user=test_setup["user1"],
        db=db_session
    )
    assert hist1.total == 1
    assert len(hist1.executions) == 1
    item = hist1.executions[0]
    assert item.tool_id == str(test_setup["tool1"].id)
    assert item.tool_name == "tool_ws1"
    assert item.status == "COMPLETED"
    assert item.duration_ms is not None
    # Verify sensitive token is redacted in preview
    assert item.result_preview is not None
    assert "[REDACTED]" in item.result_preview or "sensitive_secret_token" not in item.result_preview

    # Query for User 2 (no executions in WS2)
    hist2 = get_mcp_execution_history(
        status_filter=None,
        limit=50,
        offset=0,
        current_user=test_setup["user2"],
        db=db_session
    )
    assert hist2.total == 0
    assert len(hist2.executions) == 0

def test_mcp_execution_history_status_filtering(db_session: Session, test_setup):
    from app.api.v1.endpoints.mcp import get_mcp_execution_history

    # Query with matching status
    completed_hist = get_mcp_execution_history(
        status_filter="COMPLETED",
        limit=50,
        offset=0,
        current_user=test_setup["user1"],
        db=db_session
    )
    assert completed_hist.total == 1

    # Query with non-matching status
    failed_hist = get_mcp_execution_history(
        status_filter="FAILED",
        limit=50,
        offset=0,
        current_user=test_setup["user1"],
        db=db_session
    )
    assert failed_hist.total == 0
