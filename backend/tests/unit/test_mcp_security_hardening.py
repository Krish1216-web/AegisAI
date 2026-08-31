import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, WorkspaceMember, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPServerStatus, MCPCapabilityType, MCPTransport, MCPAuthenticationType
from app.core.mcp.security import CredentialStore
from app.services.mcp.mcp_security import MCPSecurityService, MCPSecurityDecisionEnum, MCPSecurityReasonCode

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_credential_deep_redaction():
    payload = {
        "user": "alice",
        "api_key": "secret-12345",
        "nested": {
            "bearer_token": "token-999",
            "safe_field": "public_data",
            "deep": {
                "password": "super_secret_password"
            }
        },
        "list_items": [
            {"client_secret": "secret_abc"},
            {"normal_val": 42}
        ]
    }
    redacted = CredentialStore.redact_sensitive_dict(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["bearer_token"] == "[REDACTED]"
    assert redacted["nested"]["safe_field"] == "public_data"
    assert redacted["nested"]["deep"]["password"] == "[REDACTED]"
    assert redacted["list_items"][0]["client_secret"] == "[REDACTED]"
    assert redacted["list_items"][1]["normal_val"] == 42

def test_rbac_permission_matrix(db_session: Session):
    sec_service = MCPSecurityService(db_session)
    role_user = Role(id=uuid.uuid4(), name="User")
    role_admin = Role(id=uuid.uuid4(), name="Admin")
    db_session.add_all([role_user, role_admin])
    db_session.flush()

    user = User(id=uuid.uuid4(), email="u@test.com", username="u1", password_hash="pw", role_id=role_user.id, is_active=True)
    admin = User(id=uuid.uuid4(), email="a@test.com", username="a1", password_hash="pw", role_id=role_admin.id, is_active=True)
    db_session.add_all([user, admin])
    db_session.commit()

    # Regular user checks
    assert sec_service.check_rbac_permission(user, "mcp:tool:execute") is True
    assert sec_service.check_rbac_permission(user, "mcp:resource:read") is True
    assert sec_service.check_rbac_permission(user, "mcp:prompt:render") is True
    assert sec_service.check_rbac_permission(user, "mcp:server:manage") is False
    assert sec_service.check_rbac_permission(user, "mcp:admin") is False

    # Admin checks
    assert sec_service.check_rbac_permission(admin, "mcp:server:manage") is True
    assert sec_service.check_rbac_permission(admin, "mcp:admin") is True

def test_security_evaluation_precedence_disabled_server(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    role = Role(id=uuid.uuid4(), name="Admin")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS")
    admin = User(id=uuid.uuid4(), email="admin@test.com", username="admin", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, admin])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="admin")
    db_session.add(mem)

    # Disabled server
    server = MCPServer(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=admin.id,
        name="disabled-server",
        server_url="http://localhost:8000/sse",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.DISABLED,
        enabled=False,
        authentication_type=MCPAuthenticationType.NONE
    )
    db_session.add(server)
    db_session.flush()

    tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="safe_tool",
        description="A safe tool on a disabled server",
        enabled=True,
        is_stale=False
    )
    db_session.add(tool)
    db_session.commit()

    sec_service = MCPSecurityService(db_session)
    decision = sec_service.evaluate_tool_execution(admin.id, ws.id, tool.id, arguments={})
    # Even though user is Admin and tool is Safe, Server Disabled takes precedence
    assert decision.decision == MCPSecurityDecisionEnum.DENY
    assert decision.reason_code == MCPSecurityReasonCode.SERVER_DISABLED
