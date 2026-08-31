import pytest
import uuid
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.mcp import MCPServer, MCPCapability, MCPTransport, MCPServerStatus, MCPCapabilityType
from app.core.agent.pipeline import AegisAIPipeline
from app.core.agent.checkpoint import InMemoryCheckpointer
from app.services.ai_service import AIService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Pipeline Integration Org")
    role = Role(id=uuid.uuid4(), name="User")
    session.add_all([org, role])
    session.commit()

    u1 = User(id=uuid.uuid4(), email="pipe_user1@test.com", username="pipe1", password_hash="pw", role_id=role.id, is_active=True)
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Pipeline")
    session.add_all([u1, ws1])
    session.commit()

    mem = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws1.id, user_id=u1.id, role="member")
    session.add(mem)
    session.commit()

    server = MCPServer(
        id=uuid.uuid4(),
        user_id=u1.id,
        workspace_id=ws1.id,
        name="Mock MCP Pipeline Server",
        server_url="mock://pipeline-test",
        transport=MCPTransport.SSE,
        status=MCPServerStatus.ACTIVE,
        enabled=True
    )
    session.add(server)
    session.commit()

    # Safe tool
    safe_tool = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.TOOL,
        name="calculate_sum",
        description="Math addition helper",
        input_schema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        enabled=True,
        is_stale=False
    )
    # Resource
    resource = MCPCapability(
        id=uuid.uuid4(),
        server_id=server.id,
        capability_type=MCPCapabilityType.RESOURCE,
        name="connected_project_spec",
        description="Connected documentation",
        input_schema={"uri": "workspace://docs/project.md"},
        enabled=True,
        is_stale=False
    )
    session.add_all([safe_tool, resource])
    session.commit()

    yield session
    session.close()

@pytest.fixture
def mock_ai_service():
    class MockAIService:
        pass
    return MockAIService()

@pytest.mark.asyncio
async def test_full_pipeline_mcp_tool_execution(db_session, mock_ai_service):
    user = db_session.query(User).filter_by(email="pipe_user1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Pipeline").first()

    checkpointer = InMemoryCheckpointer()
    pipeline = AegisAIPipeline(ai_service=mock_ai_service, checkpointer=checkpointer, db=db_session)

    state = pipeline.build_initial_state(
        user_id=str(user.id),
        workspace_id=str(ws.id),
        execution_id=str(uuid.uuid4()),
        original_prompt="use mcp calculator to add numbers",
        provider="mock",
        model="mock-gpt"
    )

    result = await pipeline.execute(state)

    assert result["final_response"] is not None
    assert len(result.get("tool_results", [])) >= 1

@pytest.mark.asyncio
async def test_full_pipeline_mcp_resource_reading(db_session, mock_ai_service):
    user = db_session.query(User).filter_by(email="pipe_user1@test.com").first()
    ws = db_session.query(Workspace).filter_by(name="WS Pipeline").first()

    checkpointer = InMemoryCheckpointer()
    pipeline = AegisAIPipeline(ai_service=mock_ai_service, checkpointer=checkpointer, db=db_session)

    state = pipeline.build_initial_state(
        user_id=str(user.id),
        workspace_id=str(ws.id),
        execution_id=str(uuid.uuid4()),
        original_prompt="read my connected project documentation and summarize it",
        provider="mock",
        model="mock-gpt"
    )

    result = await pipeline.execute(state)

    assert result["final_response"] is not None
    assert len(result.get("tool_results", [])) >= 1
    assert result["tool_results"][0]["metadata"]["source"] == "MCP_RESOURCE"
    assert "MCP Resource Evidence" in result["final_response"] or "Mock resource content" in result["final_response"]
