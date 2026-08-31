import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_tool_executor import (
    MCPToolExecutionService,
    generate_tool_confirmation_token,
    verify_and_consume_confirmation_token
)
from app.core.mcp.base import MCPToolConfirmationRequired, MCPValidationError
from app.core.mcp.security import CredentialStore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Security Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    u1 = User(id=uuid.uuid4(), email="sec1@test.com", username="sec1", password_hash="pw", role_id=role.id, is_active=True)
    u2 = User(id=uuid.uuid4(), email="sec2@test.com", username="sec2", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sec 1")
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sec 2")
    session.add_all([u1, u2, ws1, ws2])
    session.commit()
    
    yield session
    session.close()

@pytest.mark.asyncio
async def test_restricted_tool_confirmation_flow_and_replay_prevention(db_session):
    u1 = db_session.query(User).filter_by(email="sec1@test.com").first()
    u2 = db_session.query(User).filter_by(email="sec2@test.com").first()
    ws1 = db_session.query(Workspace).filter_by(name="WS Sec 1").first()
    ws2 = db_session.query(Workspace).filter_by(name="WS Sec 2").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=u1.id,
        workspace_id=ws1.id,
        name="Command Server",
        server_url="mock://cmd",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    # Restricted tool
    tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="execute_shell_command",
        description="Run terminal bash commands",
        input_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        },
        enabled=True,
        is_stale=False
    )
    db_session.add(tool)
    db_session.commit()

    executor = MCPToolExecutionService(db_session)
    args = {"command": "echo hello"}

    # 1. Execution without token must raise MCPToolConfirmationRequired
    with pytest.raises(MCPToolConfirmationRequired) as cr:
        await executor.execute_tool(u1.id, ws1.id, tool.id, arguments=args)
    assert cr.value.tool_id == str(tool.id)

    # 2. Generate valid confirmation token
    token = generate_tool_confirmation_token(u1.id, ws1.id, tool.id, args, expires_in_seconds=60)
    assert token is not None

    # 3. Wrong user cannot use token
    with pytest.raises(MCPValidationError) as exc_u2:
        await executor.execute_tool(u2.id, ws1.id, tool.id, arguments=args, confirmation_token=token)
    assert "MCP tool not found or access denied" in str(exc_u2.value)

    # 4. Correct execution with valid token
    res = await executor.execute_tool(u1.id, ws1.id, tool.id, arguments=args, confirmation_token=token)
    assert res.status == "SUCCESS"

    # 5. Replay attempt: Token was consumed once and must be rejected on second run
    with pytest.raises(MCPValidationError) as exc_replay:
        await executor.execute_tool(u1.id, ws1.id, tool.id, arguments=args, confirmation_token=token)
    assert "Invalid or expired tool execution confirmation token" in str(exc_replay.value)

def test_credential_and_secret_redaction():
    raw_output = {
        "api_key": "sk-live-supersecret123456",
        "authorization": "Bearer eyJhbGciOi...",
        "result": "Query succeeded",
        "nested": {
            "password": "my_db_password",
            "safe_data": 42
        }
    }
    redacted = CredentialStore.redact_sensitive_dict(raw_output)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["safe_data"] == 42
    assert redacted["result"] == "Query succeeded"
