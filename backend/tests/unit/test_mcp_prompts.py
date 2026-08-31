import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_prompt_service import MCPPromptService
from app.core.mcp.base import MCPValidationError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Prompt Test Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    u1 = User(id=uuid.uuid4(), email="p_u1@test.com", username="p_u1", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Prompt")
    session.add_all([u1, ws1])
    session.commit()
    
    yield session
    session.close()

@pytest.mark.asyncio
async def test_prompt_listing_and_rendering(db_session):
    user = db_session.query(User).filter_by(email="p_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Prompt").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Template Server",
        server_url="mock://templates",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    prompt1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.PROMPT,
        name="audit_code_security",
        description="Audit source code for security vulnerabilities",
        input_schema={
            "arguments": [
                {"name": "code", "description": "Source code text", "required": True},
                {"name": "language", "description": "Programming language", "required": False}
            ]
        },
        enabled=True,
        is_stale=False
    )
    db_session.add(prompt1)
    db_session.commit()

    service = MCPPromptService(db_session)

    # 1. List Prompts
    items, total = service.list_prompts(user.id, ws.id)
    assert total == 1
    assert items[0]["name"] == "audit_code_security"
    assert len(items[0]["arguments"]) == 2

    # 2. Get Prompt
    single = service.get_prompt(user.id, ws.id, prompt1.id)
    assert single is not None
    assert single["name"] == "audit_code_security"

    # 3. Render Prompt with valid arguments
    render_res = await service.render_prompt(
        user.id, ws.id, prompt1.id,
        arguments={"code": "def eval_input(x): eval(x)", "language": "python"}
    )
    assert render_res.name == "audit_code_security"
    assert len(render_res.messages) == 1
    assert render_res.messages[0].role == "user"
    assert "eval_input" in render_res.messages[0].content
    assert render_res.untrusted is True

    # 4. Search Prompts
    search_res = service.search_prompts(user.id, ws.id, query="security")
    assert len(search_res) == 1
    assert search_res[0]["id"] == prompt1.id

@pytest.mark.asyncio
async def test_prompt_validation_and_rejections(db_session):
    user = db_session.query(User).filter_by(email="p_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Prompt").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Server Prompts Rejection",
        server_url="mock://rej-p",
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    prompt = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.PROMPT,
        name="audit_code_security",
        input_schema={
            "arguments": [
                {"name": "code", "required": True}
            ]
        },
        enabled=True,
        is_stale=False
    )
    db_session.add(prompt)
    db_session.commit()

    service = MCPPromptService(db_session)

    # 1. Missing required argument
    with pytest.raises(MCPValidationError) as exc1:
        await service.render_prompt(user.id, ws.id, prompt.id, arguments={})
    assert "Missing required prompt argument: 'code'" in str(exc1.value)

    # 2. Disabled prompt
    service.toggle_prompt(user.id, ws.id, prompt.id, enabled=False)
    with pytest.raises(MCPValidationError) as exc2:
        await service.render_prompt(user.id, ws.id, prompt.id, arguments={"code": "pass"})
    assert "is disabled" in str(exc2.value)

    # 3. Stale prompt
    service.toggle_prompt(user.id, ws.id, prompt.id, enabled=True)
    prompt.is_stale = True
    db_session.commit()
    with pytest.raises(MCPValidationError) as exc3:
        await service.render_prompt(user.id, ws.id, prompt.id, arguments={"code": "pass"})
    assert "is stale" in str(exc3.value)
