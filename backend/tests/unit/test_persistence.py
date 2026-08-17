import pytest
import uuid
import json
import time
import datetime
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.ai import Execution, AgentExecution, ExecutionEvent, ToolExecution, ExecutionCheckpoint
from app.core.agent.postgres_checkpoint import PostgresCheckpointer
from app.core.agent.pipeline import AegisAIPipeline
from app.core.agent.state import ExecutionStatus
from app.core.agent.exceptions import MemoryPermissionError, GraphExecutionError
from app.core.agent.tools import generate_confirmation_token
from app.services.ai_service import AIService

@pytest.fixture
def db_session():
    # Setup SQLite in-memory DB and enforce foreign key constraints
    engine = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Seed required entities for foreign key constraints
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Security Hardened Corp")
    session.add(org)
    session.commit()
    
    role_id = uuid.uuid4()
    role = Role(id=role_id, name="member")
    session.add(role)
    session.commit()
        
    user = User(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="auditor@aegis.ai",
        username="auditor",
        password_hash="secure_hash_here",
        role_id=role_id,
        is_active=True
    )
    session.add(user)
    
    workspace = Workspace(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        organization_id=org_id,
        name="Auditing Workspace"
    )
    session.add(workspace)
    session.commit()
    
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def mock_redis():
    class LocalMockRedis:
        def __init__(self):
            self.data = {}
            self.expires = {}
        def set(self, key, val, ex=None, px=None, nx=False, xx=False):
            if nx and key in self.data:
                return False
            self.data[key] = val
            return True
        def get(self, key):
            return self.data.get(key)
        def delete(self, *keys):
            for k in keys:
                self.data.pop(k, None)
        def incr(self, key):
            val = int(self.data.get(key, 0)) + 1
            self.data[key] = str(val)
            return val
        def expire(self, key, seconds):
            self.expires[key] = seconds
            return True
    return LocalMockRedis()

@pytest.mark.asyncio
async def test_postgres_checkpointer_isolation(db_session):
    checkpointer = PostgresCheckpointer(db_session)
    exec_id = str(uuid.uuid4())
    user_id = "11111111-1111-1111-1111-111111111111"
    workspace_id = "22222222-2222-2222-2222-222222222222"
    
    # Save base mock execution first to satisfy FK constraint on checkpoint
    execution = Execution(
        id=uuid.UUID(exec_id),
        user_id=uuid.UUID(user_id),
        workspace_id=uuid.UUID(workspace_id),
        status="RUNNING",
        original_request="Test prompt",
        started_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(execution)
    db_session.commit()
    
    state = {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "current_agent": "OrchestratorAgent",
        "execution_status": "RUNNING",
        "original_prompt": "Audit systems"
    }
    
    # Test Save
    checkpointer.save(exec_id, state)
    assert checkpointer.exists(exec_id) is True
    
    # Test Load matching user
    loaded = checkpointer.load(exec_id, user_id=user_id, workspace_id=workspace_id)
    assert loaded is not None
    assert loaded["current_agent"] == "OrchestratorAgent"
    
    # Test Load tenant isolation mismatch (different user)
    with pytest.raises(MemoryPermissionError):
        checkpointer.load(exec_id, user_id=str(uuid.uuid4()), workspace_id=workspace_id)
        
    # Test Load workspace isolation mismatch (different workspace)
    with pytest.raises(MemoryPermissionError):
        checkpointer.load(exec_id, user_id=user_id, workspace_id=str(uuid.uuid4()))
        
    # Test Delete
    checkpointer.delete(exec_id)
    assert checkpointer.exists(exec_id) is False

@pytest.mark.asyncio
async def test_pipeline_execution_persistence(db_session, mock_redis):
    # Mock LLM calls
    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.redis = mock_redis
    mock_ai_service.db = db_session
    
    checkpointer = PostgresCheckpointer(db_session)
    pipeline = AegisAIPipeline(mock_ai_service, checkpointer=checkpointer, db=db_session)
    
    exec_id = str(uuid.uuid4())
    user_id = "11111111-1111-1111-1111-111111111111"
    workspace_id = "22222222-2222-2222-2222-222222222222"
    
    state = pipeline.build_initial_state(
        user_id=user_id,
        workspace_id=workspace_id,
        execution_id=exec_id,
        original_prompt="Calculate 250 * 12 mock",
        provider="openai",
        model="gpt-4o-mini"
    )
    
    # Set simulated token usage to verify cost calculation
    state["token_usage"] = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
    
    # Execute Pipeline
    final_state = await pipeline.execute(state)
    
    # Verify Execution Persistence
    exec_uuid = uuid.UUID(exec_id)
    execution = db_session.query(Execution).filter(Execution.id == exec_uuid).first()
    assert execution is not None
    assert execution.status == "COMPLETED"
    assert execution.original_request == "Calculate 250 * 12 mock"
    assert execution.critic_score is not None
    assert execution.response_confidence == 0.99
    
    # Verify Cost calculation in metadata
    meta = execution.meta_data
    assert meta["input_cost"] is not None
    assert meta["output_cost"] is not None
    assert meta["total_cost"] is not None
    
    # Verify Agent Runs Persistence
    agent_runs = db_session.query(AgentExecution).filter(AgentExecution.execution_id == exec_uuid).all()
    assert len(agent_runs) > 0
    assert any(ar.agent_type == "OrchestratorAgent" and ar.status == "COMPLETED" for ar in agent_runs)
    
    # Verify Events Logged
    events = db_session.query(ExecutionEvent).filter(ExecutionEvent.execution_id == exec_uuid).all()
    assert len(events) > 0
    event_types = {e.event_type for e in events}
    assert "ExecutionStarted" in event_types
    assert "AgentCompleted" in event_types
    assert "ExecutionCompleted" in event_types

@pytest.mark.asyncio
async def test_resume_confirmation_cancel_flow(db_session, mock_redis):
    mock_ai_service = MagicMock(spec=AIService)
    mock_ai_service.redis = mock_redis
    mock_ai_service.db = db_session
    
    checkpointer = PostgresCheckpointer(db_session)
    pipeline = AegisAIPipeline(mock_ai_service, checkpointer=checkpointer, db=db_session)
    
    exec_id = str(uuid.uuid4())
    user_id = "11111111-1111-1111-1111-111111111111"
    workspace_id = "22222222-2222-2222-2222-222222222222"
    
    # Run execution that prompts confirmation
    state = pipeline.build_initial_state(
        user_id=user_id,
        workspace_id=workspace_id,
        execution_id=exec_id,
        original_prompt="Get Seattle weather mock",
        provider="mock"
    )
    
    # 1. Execute initially (expects paused/waiting inside execution outcomes)
    res_state = await pipeline.execute(state)
    
    # Verify tool execution requires confirmation in DB
    tool_execs = db_session.query(ToolExecution).filter(ToolExecution.execution_id == uuid.UUID(exec_id)).all()
    assert len(tool_execs) == 1
    assert tool_execs[0].status == "REQUIRES_CONFIRMATION"
    
    # Get the confirmation token
    token = res_state["tool_results"][0]["metadata"]["confirmation_token"]
    
    # 2. Test Resume Confirmation
    confirm_state = await pipeline.resume_after_confirmation(exec_id, user_id, workspace_id, token)
    
    # Tool execution status must be COMPLETED now
    tool_execs_after = db_session.query(ToolExecution).filter(ToolExecution.execution_id == uuid.UUID(exec_id)).all()
    assert any(te.status == "COMPLETED" for te in tool_execs_after)
    
    # 3. Test Cancel
    cancel_state = await pipeline.cancel(exec_id, user_id, workspace_id)
    assert cancel_state["execution_status"] == ExecutionStatus.CANCELLED
    
    db_exec = db_session.query(Execution).filter(Execution.id == uuid.UUID(exec_id)).first()
    assert db_exec.status == "CANCELLED"
