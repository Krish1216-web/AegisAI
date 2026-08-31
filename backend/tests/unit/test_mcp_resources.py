import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.services.mcp.mcp_resource_service import MCPResourceService
from app.core.mcp.base import MCPValidationError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Resource Test Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()
    
    u1 = User(id=uuid.uuid4(), email="res_u1@test.com", username="res_u1", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Res")
    session.add_all([u1, ws1])
    session.commit()
    
    yield session
    session.close()

@pytest.mark.asyncio
async def test_resource_listing_and_reading(db_session):
    user = db_session.query(User).filter_by(email="res_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Res").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Docs Server",
        server_url="mock://docs",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    res1 = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="Architecture Docs",
        description="System design document",
        input_schema={"uri": "workspace://docs/architecture.md", "mime_type": "text/markdown"},
        enabled=True,
        is_stale=False
    )
    res2 = db_session.add(res1)
    db_session.commit()

    service = MCPResourceService(db_session)

    # 1. List Resources
    items, total = service.list_resources(user.id, ws.id)
    assert total == 1
    assert items[0]["name"] == "Architecture Docs"
    assert items[0]["uri"] == "workspace://docs/architecture.md"

    # 2. Get Resource
    single = service.get_resource(user.id, ws.id, res1.id)
    assert single is not None
    assert single["mime_type"] == "text/markdown"

    # 3. Read Resource Content
    content = await service.read_resource(user.id, ws.id, res1.id)
    assert content.uri == "workspace://docs/architecture.md"
    assert "# AegisAI Architecture" in content.text
    assert content.size > 0
    assert content.truncated is False

    # 4. Search Resources
    search_res = service.search_resources(user.id, ws.id, query="Architecture")
    assert len(search_res) == 1
    assert search_res[0]["id"] == res1.id

@pytest.mark.asyncio
async def test_resource_disabled_and_stale_rejections(db_session):
    user = db_session.query(User).filter_by(email="res_u1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Res").first()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Server Rejections",
        server_url="mock://rej",
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    db_session.add(server)
    db_session.commit()

    res = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="Schema Resource",
        input_schema={"uri": "db://schema/public", "mime_type": "application/json"},
        enabled=True,
        is_stale=False
    )
    db_session.add(res)
    db_session.commit()

    service = MCPResourceService(db_session)

    # 1. Disable resource
    service.toggle_resource(user.id, ws.id, res.id, enabled=False)
    with pytest.raises(MCPValidationError) as exc1:
        await service.read_resource(user.id, ws.id, res.id)
    assert "is disabled" in str(exc1.value)

    # 2. Re-enable resource, mark stale
    service.toggle_resource(user.id, ws.id, res.id, enabled=True)
    res.is_stale = True
    db_session.commit()
    with pytest.raises(MCPValidationError) as exc2:
        await service.read_resource(user.id, ws.id, res.id)
    assert "is stale" in str(exc2.value)

    # 3. Disable server
    res.is_stale = False
    server.enabled = False
    db_session.commit()
    with pytest.raises(MCPValidationError) as exc3:
        await service.read_resource(user.id, ws.id, res.id)
    assert "MCP server 'Server Rejections' is disabled" in str(exc3.value)
