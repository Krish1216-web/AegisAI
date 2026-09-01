import pytest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.capability import (
    CapabilityMetadata,
    CapabilityType,
    platform_capability_registry
)
from app.core.platform.agent_bridge import AgentContextBridge
from app.core.platform.agent_adapter import AgentCapabilityAdapter
from app.core.platform.provenance import (
    ProvenanceSourceType,
    ProvenanceTrustLevel
)
from app.core.platform.events import (
    PlatformEventType,
    PlatformEvent,
    PlatformEventDispatcher
)
from app.core.agent.state import AgentState, ExecutionStatus
from app.services.platform_execution import PlatformExecutionService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def agent_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Agent Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Agent")
    user = User(
        id=uuid.uuid4(),
        email="agent_user@test.com",
        username="agent_user",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_agent_context_bridge_platform_to_agent_state(agent_setup):
    ws = agent_setup["ws"]
    user = agent_setup["user"]

    sec_ctx = SecurityContext(
        user_id=user.id,
        workspace_id=ws.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user.id,
        workspace_id=ws.id,
        security_context=sec_ctx,
        session_id="conv-session-123"
    )

    input_data = {
        "query": "Synthesize financial intelligence and quarterly revenue",
        "provider": "openai",
        "model": "gpt-4o-mini"
    }

    state = AgentContextBridge.platform_context_to_agent_state(context, input_data)

    assert state["user_id"] == str(user.id)
    assert state["workspace_id"] == str(ws.id)
    assert state["original_prompt"] == "Synthesize financial intelligence and quarterly revenue"
    assert state["conversation_id"] == "conv-session-123"
    assert state["execution_status"] == ExecutionStatus.PENDING
    assert state["metadata"]["provider"] == "openai"

def test_agent_context_bridge_agent_to_execution_output(agent_setup):
    ws = agent_setup["ws"]
    user = agent_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    dummy_state: AgentState = {
        "request_id": "req-123",
        "user_id": str(user.id),
        "workspace_id": str(ws.id),
        "original_prompt": "Analyze market trends",
        "execution_status": ExecutionStatus.COMPLETED,
        "execution_plan": ["Fetch RAG context", "Query Knowledge Graph", "Synthesize findings"],
        "final_response": "Quarterly revenues increased by 14% based on market report.",
        "critic_decision": "APPROVED",
        "confidence_score": 0.96,
        "rag_citations": [
            {
                "document_id": "doc_report_2026",
                "document_title": "Q2 2026 Earnings Report",
                "text_snippet": "Revenues up 14% year over year.",
                "relevance_score": 0.95
            }
        ],
        "graph_citations": [
            {
                "entity_id": "ent_aegis",
                "name": "AegisAI Corp",
                "description": "Enterprise AI Security Platform"
            }
        ],
        "mcp_citations": [
            {
                "tool_name": "fetch_stock_price",
                "result": "$142.50"
            }
        ]
    }

    output, provenance_items = AgentContextBridge.agent_state_to_execution_output(dummy_state, context)

    assert "Quarterly revenues increased" in output["response"]
    assert len(output["plan"]) == 3
    assert output["critic_decision"] == "APPROVED"
    assert output["confidence_score"] == 0.96

    # Verify Provenance mappings
    assert len(provenance_items) == 4
    source_types = [p.source_type for p in provenance_items]
    trust_levels = [p.trust_level for p in provenance_items]

    assert ProvenanceSourceType.DOCUMENT_CHUNK in source_types
    assert ProvenanceSourceType.GRAPH_NODE in source_types
    assert ProvenanceSourceType.MCP_TOOL in source_types
    assert ProvenanceSourceType.AGENT_REASONING in source_types

    assert ProvenanceTrustLevel.VERIFIED_RAG in trust_levels
    assert ProvenanceTrustLevel.VERIFIED_GRAPH in trust_levels
    assert ProvenanceTrustLevel.UNTRUSTED_MCP in trust_levels
    assert ProvenanceTrustLevel.TRUSTED_INTERNAL in trust_levels

def test_agent_capability_adapter_execution(db_session: Session, agent_setup):
    ws = agent_setup["ws"]
    user = agent_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="agent.orchestrator",
        context=context,
        input_data={"query": "Perform comprehensive intelligence audit"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert "response" in res.output
    assert len(res.provenance) >= 1
    assert res.output["critic_decision"] in ["APPROVED", "ACCEPT"]

def test_agent_capability_validation_and_events(db_session: Session, agent_setup):
    ws = agent_setup["ws"]
    user = agent_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    # 1. Validation error on empty query
    res_empty = service.execute("agent.orchestrator", context, {"query": "   "})
    assert res_empty.status == LifecycleState.FAILED
    assert "INVALID_EXECUTION_INPUT" in res_empty.errors[0]["code"]

    # 2. Event emission verification
    captured_events = []
    def event_listener(evt: PlatformEvent):
        captured_events.append(evt)

    PlatformEventDispatcher.subscribe(PlatformEventType.AGENT_EVENT, event_listener)

    res_valid = service.execute("agent.orchestrator", context, {"query": "Test query with events"})
    assert res_valid.status == LifecycleState.COMPLETED
    assert len(captured_events) >= 1
    actions = [e.payload.get("action") for e in captured_events]
    assert "agent_execution_started" in actions
