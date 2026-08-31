import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, WorkspaceMember, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPServerStatus, MCPCapabilityType, MCPTransport, MCPAuthenticationType
from app.services.mcp.mcp_security import MCPSecurityService, MCPSecurityDecisionEnum, MCPSecurityReasonCode
from app.services.mcp.mcp_tool_catalog import MCPToolCatalogService
from app.services.mcp.mcp_resource_service import MCPResourceService
from app.services.mcp.mcp_prompt_service import MCPPromptService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def multi_tenant_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Multi Tenant Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    # Tenant 1
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS 1")
    u1 = User(id=uuid.uuid4(), email="u1@test.com", username="u1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws1, u1])
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=ws1.id, user_id=u1.id, role="member"))

    s1 = MCPServer(
        id=uuid.uuid4(), workspace_id=ws1.id, user_id=u1.id, name="srv1",
        server_url="http://localhost:8001/sse", transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE, enabled=True, authentication_type=MCPAuthenticationType.NONE
    )
    db_session.add(s1)
    db_session.flush()

    t1 = MCPCapability(id=uuid.uuid4(), server_id=s1.id, capability_type=MCPCapabilityType.TOOL, name="tool1", enabled=True, is_stale=False)
    r1 = MCPCapability(id=uuid.uuid4(), server_id=s1.id, capability_type=MCPCapabilityType.RESOURCE, name="res1", input_schema={"uri": "workspace://ws1/doc"}, enabled=True, is_stale=False)
    p1 = MCPCapability(id=uuid.uuid4(), server_id=s1.id, capability_type=MCPCapabilityType.PROMPT, name="prm1", enabled=True, is_stale=False)
    db_session.add_all([t1, r1, p1])

    # Tenant 2
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS 2")
    u2 = User(id=uuid.uuid4(), email="u2@test.com", username="u2", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws2, u2])
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=ws2.id, user_id=u2.id, role="member"))

    s2 = MCPServer(
        id=uuid.uuid4(), workspace_id=ws2.id, user_id=u2.id, name="srv2",
        server_url="http://localhost:8002/sse", transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE, enabled=True, authentication_type=MCPAuthenticationType.NONE
    )
    db_session.add(s2)
    db_session.flush()

    t2 = MCPCapability(id=uuid.uuid4(), server_id=s2.id, capability_type=MCPCapabilityType.TOOL, name="tool2", enabled=True, is_stale=False)
    db_session.add(t2)
    db_session.commit()

    return {"u1": u1, "ws1": ws1, "s1": s1, "t1": t1, "r1": r1, "p1": p1, "u2": u2, "ws2": ws2, "s2": s2, "t2": t2}

def test_cross_tenant_tool_catalog_isolation(db_session: Session, multi_tenant_setup):
    s = multi_tenant_setup
    catalog = MCPToolCatalogService(db_session)
    
    # User 1 queries tools in WS 1
    tools_ws1, total_ws1 = catalog.list_tools(s["u1"].id, s["ws1"].id)
    assert total_ws1 == 1
    assert tools_ws1[0]["name"] == "tool1"

    # User 1 attempts to query tool2 (from WS 2) within WS 1 context -> None
    t2_lookup = catalog.get_tool(s["u1"].id, s["ws1"].id, s["t2"].id)
    assert t2_lookup is None

    # User 1 attempts to pass WS 2 directly -> denied
    tools_cross, total_cross = catalog.list_tools(s["u1"].id, s["ws2"].id)
    assert total_cross == 0

def test_cross_tenant_security_evaluation_rejection(db_session: Session, multi_tenant_setup):
    s = multi_tenant_setup
    sec_service = MCPSecurityService(db_session)

    # User 2 attempts to evaluate tool from WS 1
    dec = sec_service.evaluate_tool_execution(s["u2"].id, s["ws2"].id, s["t1"].id, arguments={})
    assert dec.decision == MCPSecurityDecisionEnum.DENY
    assert dec.reason_code in (MCPSecurityReasonCode.TENANT_MISMATCH, MCPSecurityReasonCode.TOOL_ACCESS_DENIED)

def test_cross_tenant_resource_and_prompt_isolation(db_session: Session, multi_tenant_setup):
    s = multi_tenant_setup
    res_svc = MCPResourceService(db_session)
    prm_svc = MCPPromptService(db_session)

    # User 2 cannot access resource from WS 1
    res = res_svc.get_resource(s["u2"].id, s["ws2"].id, s["r1"].id)
    assert res is None

    # User 2 cannot access prompt from WS 1
    prm = prm_svc.get_prompt(s["u2"].id, s["ws2"].id, s["p1"].id)
    assert prm is None
