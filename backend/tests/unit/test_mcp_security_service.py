import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_security import (
    MCPSecurityService,
    MCPSecurityDecisionEnum,
    MCPSecurityReasonCode,
    MCPTrustLabel
)
from app.services.mcp.mcp_tool_executor import generate_tool_confirmation_token

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Security Service Test Org")
    role_user = Role(id=uuid.uuid4(), name="User")
    role_admin = Role(id=uuid.uuid4(), name="Admin")
    session.add_all([org, role_user, role_admin])
    session.commit()

    u1 = User(id=uuid.uuid4(), email="sec_u1@test.com", username="sec_u1", password_hash="pw", role_id=role_user.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sec")
    session.add_all([u1, ws1])
    session.commit()

    mem1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws1.id, user_id=u1.id, role="member")
    session.add(mem1)
    session.commit()

    yield session
    session.close()

def test_mcp_security_service_evaluation_hierarchy(db_session):
    user = db_session.query(User).filter_by(email="sec_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Sec").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Sec Server",
        server_url="mock://sec-srv",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    # 1. SAFE Tool
    safe_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        description="Adds two numbers safely",
        input_schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
        enabled=True,
        is_stale=False
    )
    # 2. RESTRICTED Tool
    restricted_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="execute_sql_query",
        description="Executes arbitrary database query",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        enabled=True,
        is_stale=False
    )
    # 3. INVALID Tool (violates schema property count limit > 50)
    invalid_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="oversized_schema_tool",
        description="Tool with invalid oversized property count",
        input_schema={"type": "object", "properties": {f"prop_{i}": {"type": "string"} for i in range(55)}},
        enabled=True,
        is_stale=False
    )
    db_session.add_all([safe_tool, restricted_tool, invalid_tool])
    db_session.commit()

    sec_service = MCPSecurityService(db_session)

    # A. Evaluate Server Access
    decision_srv = sec_service.evaluate_server_access(user.id, ws.id, server.id, action="view")
    assert decision_srv.decision == MCPSecurityDecisionEnum.ALLOW
    assert decision_srv.reason_code == MCPSecurityReasonCode.SUCCESS

    # B. SAFE Tool -> ALLOW
    decision_safe = sec_service.evaluate_tool_execution(user.id, ws.id, safe_tool.id, {"a": 1, "b": 2})
    assert decision_safe.decision == MCPSecurityDecisionEnum.ALLOW
    assert decision_safe.risk_level.lower() == "safe"
    assert decision_safe.requires_confirmation is False

    # C. RESTRICTED Tool without token -> REQUIRE_CONFIRMATION
    decision_restr_no_token = sec_service.evaluate_tool_execution(user.id, ws.id, restricted_tool.id, {"query": "SELECT 1"})
    assert decision_restr_no_token.decision == MCPSecurityDecisionEnum.REQUIRE_CONFIRMATION
    assert decision_restr_no_token.requires_confirmation is True

    # D. RESTRICTED Tool with valid confirmation token -> ALLOW
    conf_token = generate_tool_confirmation_token(user.id, ws.id, restricted_tool.id, {"query": "SELECT 1"})
    decision_restr_with_token = sec_service.evaluate_tool_execution(user.id, ws.id, restricted_tool.id, {"query": "SELECT 1"}, confirmation_token=conf_token)
    assert decision_restr_with_token.decision == MCPSecurityDecisionEnum.ALLOW

    # E. INVALID Tool -> DENY
    decision_invalid = sec_service.evaluate_tool_execution(user.id, ws.id, invalid_tool.id, {})
    assert decision_invalid.decision == MCPSecurityDecisionEnum.DENY
    assert decision_invalid.reason_code == MCPSecurityReasonCode.RISK_POLICY_DENIED

    # F. Inactive / Suspended User -> DENY
    user.is_active = False
    db_session.commit()
    decision_suspended = sec_service.evaluate_server_access(user.id, ws.id, server.id)
    assert decision_suspended.decision == MCPSecurityDecisionEnum.DENY
    assert decision_suspended.reason_code == MCPSecurityReasonCode.AUTHENTICATION_REQUIRED

def test_mcp_security_status_and_audit_logging(db_session):
    user = db_session.query(User).filter_by(email="sec_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Sec").first()
    user.is_active = True
    db_session.commit()

    sec_service = MCPSecurityService(db_session)

    # 1. Check Security Status
    status = sec_service.get_security_status(user.id, ws.id)
    assert status["policy_engine_active"] is True
    assert status["confirmation_gate_active"] is True
    assert status["ssrf_defense_active"] is True
    assert "mcp:tool:execute" in status["active_permissions"]

    # 2. Log and Retrieve Audit Events
    sec_service.log_audit_event(
        event_type="MCP_SECURITY_TEST",
        user_id=user.id,
        workspace_id=ws.id,
        decision=MCPSecurityDecisionEnum.ALLOW,
        reason_code=MCPSecurityReasonCode.SUCCESS,
        metadata={"note": "Test audit entry", "api_key": "secret_abc_123"}
    )

    logs = sec_service.get_workspace_audit_log(user.id, ws.id, limit=10)
    assert len(logs) >= 1
    assert logs[0]["event_type"] == "MCP_SECURITY_TEST"
    assert logs[0]["decision"] == "ALLOW"
    # Verify sensitive data redaction in audit metadata
    assert logs[0]["metadata"]["api_key"] == "[REDACTED]"
