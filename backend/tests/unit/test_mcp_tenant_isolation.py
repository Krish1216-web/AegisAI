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
    MCPSecurityReasonCode
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org1 = Organization(id=uuid.uuid4(), name="Org 1")
    org2 = Organization(id=uuid.uuid4(), name="Org 2")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org1, org2, role])
    session.commit()

    u1 = User(id=uuid.uuid4(), email="tenant1@test.com", username="t1", password_hash="pw", role_id=role.id, is_active=True)
    u2 = User(id=uuid.uuid4(), email="tenant2@test.com", username="t2", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org1.id, name="WS Tenant 1")
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org2.id, name="WS Tenant 2")
    session.add_all([u1, u2, ws1, ws2])
    session.commit()

    mem1 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws1.id, user_id=u1.id, role="member")
    mem2 = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws2.id, user_id=u2.id, role="member")
    session.add_all([mem1, mem2])
    session.commit()

    # Create server & capabilities belonging to Tenant 1
    srv1 = MCPServer(
        id=uuid.uuid4(),
        user_id=u1.id,
        workspace_id=ws1.id,
        name="Tenant 1 Server",
        server_url="mock://tenant-1",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    session.add(srv1)
    session.commit()

    tool1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=srv1.id,
        capability_type=MCPCapabilityType.TOOL,
        name="tenant1_tool",
        input_schema={"type": "object", "properties": {}},
        enabled=True,
        is_stale=False
    )
    res1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=srv1.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="tenant1_res",
        input_schema={"uri": "workspace://t1/doc.md"},
        enabled=True,
        is_stale=False
    )
    prompt1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=srv1.id,
        capability_type=MCPCapabilityType.PROMPT,
        name="tenant1_prompt",
        input_schema={"arguments": []},
        enabled=True,
        is_stale=False
    )
    session.add_all([tool1, res1, prompt1])
    session.commit()

    yield session
    session.close()

def test_tenant_boundary_enforcement(db_session):
    u1 = db_session.query(User).filter_by(email="tenant1@test.com").first()
    u2 = db_session.query(User).filter_by(email="tenant2@test.com").first()
    ws1 = db_session.query(Workspace).filter_by(name="WS Tenant 1").first()
    ws2 = db_session.query(Workspace).filter_by(name="WS Tenant 2").first()
    srv1 = db_session.query(MCPServer).filter_by(name="Tenant 1 Server").first()
    tool1 = db_session.query(MCPCapability).filter_by(name="tenant1_tool").first()
    res1 = db_session.query(MCPCapability).filter_by(name="tenant1_res").first()
    prompt1 = db_session.query(MCPCapability).filter_by(name="tenant1_prompt").first()

    sec_service = MCPSecurityService(db_session)

    # 1. User 2 trying to access Tenant 1's Server -> DENY
    dec_srv = sec_service.evaluate_server_access(u2.id, ws2.id, srv1.id)
    assert dec_srv.decision == MCPSecurityDecisionEnum.DENY
    assert dec_srv.reason_code == MCPSecurityReasonCode.TENANT_MISMATCH

    # 2. User 2 trying to execute Tenant 1's Tool -> DENY
    dec_tool = sec_service.evaluate_tool_execution(u2.id, ws2.id, tool1.id, {})
    assert dec_tool.decision == MCPSecurityDecisionEnum.DENY
    assert dec_tool.reason_code == MCPSecurityReasonCode.TOOL_ACCESS_DENIED

    # 3. User 2 trying to read Tenant 1's Resource -> DENY
    dec_res = sec_service.evaluate_resource_read(u2.id, ws2.id, res1.id)
    assert dec_res.decision == MCPSecurityDecisionEnum.DENY
    assert dec_res.reason_code == MCPSecurityReasonCode.RESOURCE_ACCESS_DENIED

    # 4. User 2 trying to render Tenant 1's Prompt -> DENY
    dec_prompt = sec_service.evaluate_prompt_render(u2.id, ws2.id, prompt1.id, {})
    assert dec_prompt.decision == MCPSecurityDecisionEnum.DENY
    assert dec_prompt.reason_code == MCPSecurityReasonCode.PROMPT_ACCESS_DENIED

    # 5. User 1 attempting to execute in Workspace 2 (non-member) -> DENY
    dec_ws2 = sec_service.evaluate_tool_execution(u1.id, ws2.id, tool1.id, {})
    assert dec_ws2.decision == MCPSecurityDecisionEnum.DENY
    assert dec_ws2.reason_code == MCPSecurityReasonCode.WORKSPACE_ACCESS_DENIED
