import pytest
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.memory import AgentMemory
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.memory_graph_sync import MemoryGraphSyncService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=uuid.uuid4(), name="Memory Graph Sync Org")
    session.add(org)
    role = Role(id=uuid.uuid4(), name="member")
    session.add(role)
    session.commit()

    u1 = User(id=uuid.UUID("11111111-1111-1111-1111-111111111111"), email="u1@aegis.ai", username="u1", password_hash="h", role_id=role.id)
    ws1 = Workspace(id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), organization_id=org.id, name="WS 1")
    session.add_all([u1, ws1])

    u2 = User(id=uuid.UUID("22222222-2222-2222-2222-222222222222"), email="u2@aegis.ai", username="u2", password_hash="h", role_id=role.id)
    ws2 = Workspace(id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), organization_id=org.id, name="WS 2")
    session.add_all([u2, ws2])

    session.commit()

    try:
        yield session
    finally:
        session.close()

def test_memory_to_graph_synchronization(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = MemoryGraphSyncService(db_session)

    mem = AgentMemory(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        memory_type="USER_PREFERENCE",
        content="User strongly prefers Python and FastAPI for all microservices.",
        source="conversation",
        importance=0.9,
        confidence=0.95
    )
    db_session.add(mem)
    db_session.commit()

    # Sync memory into Knowledge Graph
    result = service.sync_memory_to_graph(u1, ws1, mem)
    assert result["status"] == "synced"
    assert result["nodes_synced_count"] >= 2 # Python and FastAPI

    # Verify nodes created in graph
    py_node = db_session.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.workspace_id == ws1,
        KnowledgeGraphNode.name == "Python"
    ).first()
    assert py_node is not None
    assert py_node.node_type == NodeType.SKILL.value

    # Verify provenance
    prov = py_node.meta_data.get("provenance", [])
    assert any(p.get("memory_id") == str(mem.id) for p in prov)

    # Verify User -> USES -> Python edge
    edge = db_session.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.workspace_id == ws1,
        KnowledgeGraphEdge.target_node_id == py_node.id,
        KnowledgeGraphEdge.relationship_type == RelationshipType.USES.value
    ).first()
    assert edge is not None
    assert edge.confidence >= 0.8

def test_repeated_synchronization_idempotency(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = MemoryGraphSyncService(db_session)

    mem = AgentMemory(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        memory_type="USER_PREFERENCE",
        content="User prefers PostgreSQL.",
        source="conversation",
        importance=0.8,
        confidence=0.9
    )
    db_session.add(mem)
    db_session.commit()

    # Sync twice
    service.sync_memory_to_graph(u1, ws1, mem)
    service.sync_memory_to_graph(u1, ws1, mem)

    # Must only have 1 PostgreSQL node and 1 edge
    nodes_count = db_session.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.workspace_id == ws1,
        KnowledgeGraphNode.name == "PostgreSQL"
    ).count()
    assert nodes_count == 1

    edges_count = db_session.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.workspace_id == ws1,
        KnowledgeGraphEdge.relationship_type == RelationshipType.USES.value
    ).count()
    assert edges_count == 1

def test_graph_to_memory_synchronization(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = MemoryGraphSyncService(db_session)

    node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="AegisAI",
        node_type=NodeType.PROJECT.value,
        description="Autonomous security cognitive architecture."
    )
    db_session.add(node)
    db_session.commit()

    mem = service.sync_graph_to_memory(u1, ws1, node.id)
    assert mem is not None
    assert "AegisAI" in mem.content
    assert mem.source == "knowledge_graph"
    assert mem.meta_data.get("sync_origin") == "graph_to_memory"

def test_bidirectional_loop_prevention(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = MemoryGraphSyncService(db_session)

    # Memory generated from graph sync
    mem_from_graph = AgentMemory(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        memory_type="PROJECT_CONTEXT",
        content="Knowledge Entity: Redis [SKILL]",
        source="knowledge_graph",
        importance=0.85,
        confidence=0.95,
        meta_data={"sync_origin": "graph_to_memory"}
    )
    db_session.add(mem_from_graph)
    db_session.commit()

    res = service.sync_memory_to_graph(u1, ws1, mem_from_graph)
    assert res["status"] == "skipped_loop_prevention"

def test_memory_deletion_cleanup(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = MemoryGraphSyncService(db_session)

    mem_id = uuid.uuid4()
    mem = AgentMemory(
        id=mem_id,
        user_id=u1,
        workspace_id=ws1,
        memory_type="USER_PREFERENCE",
        content="User prefers Docker.",
        source="conversation",
        importance=0.8,
        confidence=0.9
    )
    db_session.add(mem)
    db_session.commit()

    service.sync_memory_to_graph(u1, ws1, mem)
    
    # Verify edge existed
    edge_before = db_session.query(KnowledgeGraphEdge).filter(KnowledgeGraphEdge.workspace_id == ws1).first()
    assert edge_before is not None

    # Handle deletion
    cleanup_res = service.handle_memory_deletion(u1, ws1, str(mem_id))
    assert cleanup_res["edges_deleted"] >= 1

    edge_after = db_session.query(KnowledgeGraphEdge).filter(KnowledgeGraphEdge.workspace_id == ws1).first()
    assert edge_after is None

def test_tenant_isolation_in_memory_graph_sync(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ws2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    service = MemoryGraphSyncService(db_session)

    # Sync memory for User 1 in Workspace 1
    mem = AgentMemory(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        memory_type="USER_PREFERENCE",
        content="User prefers LangGraph.",
        source="conversation",
        importance=0.9,
        confidence=0.9
    )
    db_session.add(mem)
    db_session.commit()

    service.sync_memory_to_graph(u1, ws1, mem)

    # Querying from Workspace 2 must find 0 nodes and 0 edges
    w2_nodes = db_session.query(KnowledgeGraphNode).filter(KnowledgeGraphNode.workspace_id == ws2).count()
    w2_edges = db_session.query(KnowledgeGraphEdge).filter(KnowledgeGraphEdge.workspace_id == ws2).count()
    assert w2_nodes == 0
    assert w2_edges == 0
