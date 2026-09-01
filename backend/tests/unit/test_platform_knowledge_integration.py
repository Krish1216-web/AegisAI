import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.capability import CapabilityType, platform_capability_registry
from app.core.platform.knowledge_bridge import KnowledgeContextBridge
from app.core.platform.provenance import ProvenanceSourceType, ProvenanceTrustLevel
from app.core.platform.events import PlatformEventType, PlatformEvent, PlatformEventDispatcher
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
def know_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Knowledge Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Knowledge")
    user = User(
        id=uuid.uuid4(),
        email="know_user@test.com",
        username="know_user",
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

def test_knowledge_context_bridge_rag_query_bounding(know_setup):
    ws = know_setup["ws"]
    user = know_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    input_data = {
        "query": "What is the platform security model?",
        "top_k": 200, # Exceeds max 50
        "similarity_threshold": 1.8, # Exceeds max 1.0
        "graph_depth": 10 # Exceeds max 5
    }

    params = KnowledgeContextBridge.platform_context_to_rag_query(context, input_data)

    assert params["query"] == "What is the platform security model?"
    assert params["workspace_id"] == ws.id
    assert params["user_id"] == user.id
    assert params["limit"] == 50 # Capped
    assert params["similarity_threshold"] == 1.0 # Capped
    assert params["graph_depth"] == 5 # Capped

def test_knowledge_context_bridge_output_and_provenance(know_setup):
    ws = know_setup["ws"]
    user = know_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    # 1. RAG Response transformation
    rag_data = {
        "answer": "AegisAI employs multi-tenant isolation.",
        "chunks": [
            {
                "chunk_id": "chunk_sec_1",
                "document_id": "doc_sec_arch",
                "text": "All tenant data is strictly partitioned by workspace_id.",
                "score": 0.98,
                "title": "Security Blueprint"
            }
        ],
        "citations": ["doc_sec_arch"]
    }

    output, prov = KnowledgeContextBridge.rag_response_to_execution_output(rag_data, context)
    assert output["chunks_count"] == 1
    assert len(prov) == 1
    assert prov[0].source_type == ProvenanceSourceType.DOCUMENT_CHUNK
    assert prov[0].trust_level == ProvenanceTrustLevel.VERIFIED_RAG
    assert prov[0].source_id == "chunk_sec_1"

    # 2. Hybrid RAG Response transformation
    hybrid_data = {
        "answer": "Platform integration with graph and vector.",
        "document_evidence": [{"chunk_id": "c1", "text": "doc content", "score": 0.9}],
        "graph_evidence": [{"entity_id": "e1", "name": "Agent Engine", "description": "Core engine"}],
        "relationships": [{"source": "Agent Engine", "target": "Security", "type": "USES"}],
        "confidence": 0.97
    }

    h_output, h_prov = KnowledgeContextBridge.hybrid_rag_response_to_execution_output(hybrid_data, context)
    assert len(h_output["document_evidence"]) == 1
    assert len(h_output["graph_evidence"]) == 1
    assert len(h_prov) == 2
    sources = [p.source_type for p in h_prov]
    assert ProvenanceSourceType.DOCUMENT_CHUNK in sources
    assert ProvenanceSourceType.GRAPH_NODE in sources

def test_platform_rag_execution(db_session: Session, know_setup):
    ws = know_setup["ws"]
    user = know_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="knowledge.rag",
        context=context,
        input_data={"query": "Explain authentication flow"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert "answer" in res.output
    assert len(res.provenance) >= 1
    assert res.provenance[0].trust_level == ProvenanceTrustLevel.VERIFIED_RAG

def test_platform_hybrid_rag_execution(db_session: Session, know_setup):
    ws = know_setup["ws"]
    user = know_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="knowledge.hybrid_rag",
        context=context,
        input_data={"query": "Graph reasoning and vector citations"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert "document_evidence" in res.output
    assert "graph_evidence" in res.output
    assert len(res.provenance) >= 2

def test_platform_graph_execution(db_session: Session, know_setup):
    ws = know_setup["ws"]
    user = know_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    service = PlatformExecutionService(db_session)

    res = service.execute(
        capability_id="knowledge.graph",
        context=context,
        input_data={"entity": "Platform Security Engine"}
    )

    assert res.status == LifecycleState.COMPLETED
    assert res.output["nodes_count"] >= 1
    assert len(res.provenance) >= 1
    assert res.provenance[0].trust_level == ProvenanceTrustLevel.VERIFIED_GRAPH

def test_platform_knowledge_events(db_session: Session, know_setup):
    ws = know_setup["ws"]
    user = know_setup["user"]

    sec_ctx = SecurityContext(user_id=user.id, workspace_id=ws.id, user_role="admin")
    context = PlatformContext(user_id=user.id, workspace_id=ws.id, security_context=sec_ctx)

    captured_events = []
    def event_listener(evt: PlatformEvent):
        captured_events.append(evt)

    PlatformEventDispatcher.subscribe(PlatformEventType.RAG_EVENT, event_listener)

    service = PlatformExecutionService(db_session)
    res = service.execute("knowledge.rag", context, {"query": "Event testing query"})

    assert res.status == LifecycleState.COMPLETED
    assert len(captured_events) >= 1
    actions = [e.payload.get("action") for e in captured_events]
    assert "rag_retrieval_started" in actions
