import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.document import Document, DocumentChunk
from app.models.memory import AgentMemory
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.schemas.knowledge_graph import NodeCreate, NodeUpdate, EdgeCreate
from app.services.knowledge_graph import (
    KnowledgeGraphService,
    NodeNotFound,
    EdgeNotFound,
    DuplicateEdgeError
)

# In-memory SQLite engine for unit tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)

USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
WS_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
WS_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

@pytest.fixture(name="db")
def db_fixture():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Clear tables
    session.query(KnowledgeGraphEdge).delete()
    session.query(KnowledgeGraphNode).delete()
    session.query(DocumentChunk).delete()
    session.query(Document).delete()
    session.query(AgentMemory).delete()
    session.query(WorkspaceMember).delete()
    session.query(Workspace).delete()
    session.query(User).delete()
    session.query(Role).delete()
    session.query(Organization).delete()
    session.commit()

    org = Organization(id=uuid.uuid4(), name="Test KG Org")
    session.add(org)
    session.commit()

    role = Role(id=uuid.uuid4(), name="User")
    session.add(role)
    session.commit()

    # User A in Workspace A
    ws_a = Workspace(id=WS_A_ID, organization_id=org.id, name="Workspace A")
    session.add(ws_a)
    user_a = User(
        id=USER_A_ID,
        email="user_a@aegis.ai",
        username="user_a",
        password_hash="hash_a",
        role_id=role.id,
        settings={"default_workspace_id": str(WS_A_ID)},
        is_active=True
    )
    session.add(user_a)
    session.commit()
    member_a = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_A_ID, user_id=USER_A_ID, role="owner")
    session.add(member_a)

    # User B in Workspace B
    ws_b = Workspace(id=WS_B_ID, organization_id=org.id, name="Workspace B")
    session.add(ws_b)
    user_b = User(
        id=USER_B_ID,
        email="user_b@aegis.ai",
        username="user_b",
        password_hash="hash_b",
        role_id=role.id,
        settings={"default_workspace_id": str(WS_B_ID)},
        is_active=True
    )
    session.add(user_b)
    session.commit()
    member_b = WorkspaceMember(id=uuid.uuid4(), workspace_id=WS_B_ID, user_id=USER_B_ID, role="owner")
    session.add(member_b)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(db):
    user_a = db.query(User).filter(User.id == USER_A_ID).first()

    def mock_get_current_user():
        return user_a

    def mock_check_rate_limit():
        return None

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[check_rate_limit] = mock_check_rate_limit

    try:
        yield TestClient(app, base_url="http://localhost")
    finally:
        app.dependency_overrides.clear()

# =========================================================
# 1. Node CRUD Tests
# =========================================================

def test_node_creation(db):
    service = KnowledgeGraphService(db)
    node_data = NodeCreate(
        node_type=NodeType.PROJECT.value,
        name="Project Apollo",
        description="Autonomous flight mission",
        metadata={"priority": "high", "budget": 1000000}
    )
    node = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=node_data)
    assert node.id is not None
    assert node.name == "Project Apollo"
    assert node.node_type == "PROJECT"
    assert node.meta_data == {"priority": "high", "budget": 1000000}
    assert node.user_id == USER_A_ID
    assert node.workspace_id == WS_A_ID

def test_node_retrieval(db):
    service = KnowledgeGraphService(db)
    node = service.create_node(
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        node_data=NodeCreate(node_type=NodeType.SKILL.value, name="Python Coding")
    )
    retrieved = service.get_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=node.id)
    assert retrieved is not None
    assert retrieved.id == node.id
    assert retrieved.name == "Python Coding"

def test_node_update(db):
    service = KnowledgeGraphService(db)
    node = service.create_node(
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        node_data=NodeCreate(node_type=NodeType.AGENT.value, name="Agent Alpha")
    )
    updated = service.update_node(
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        node_id=node.id,
        update_data=NodeUpdate(name="Agent Alpha v2", description="Upgraded capabilities")
    )
    assert updated.name == "Agent Alpha v2"
    assert updated.description == "Upgraded capabilities"

def test_node_deletion_cascade(db):
    service = KnowledgeGraphService(db)
    n1 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.TASK.value, name="Task 1"))
    n2 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="Agent 1"))
    
    edge = service.create_edge(
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        edge_data=EdgeCreate(source_node_id=n1.id, target_node_id=n2.id, relationship_type=RelationshipType.ASSIGNED_TO.value)
    )
    assert edge.id is not None

    # Delete n1 -> edge should be removed
    service.delete_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=n1.id)
    assert service.get_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=n1.id) is None
    assert service.get_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_id=edge.id) is None
    assert service.get_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=n2.id) is not None

# =========================================================
# 2. Edge CRUD Tests
# =========================================================

def test_edge_creation(db):
    service = KnowledgeGraphService(db)
    n1 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="Agent 1"))
    n2 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.SKILL.value, name="Skill 1"))
    
    edge = service.create_edge(
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        edge_data=EdgeCreate(
            source_node_id=n1.id,
            target_node_id=n2.id,
            relationship_type=RelationshipType.USES.value,
            confidence=0.95,
            properties={"frequency": "daily"}
        )
    )
    assert edge.id is not None
    assert edge.confidence == 0.95
    assert edge.relationship_type == "USES"
    assert edge.meta_data == {"frequency": "daily"}

def test_edge_deletion(db):
    service = KnowledgeGraphService(db)
    n1 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="Agent 1"))
    n2 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.SKILL.value, name="Skill 1"))
    edge = service.create_edge(
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        edge_data=EdgeCreate(source_node_id=n1.id, target_node_id=n2.id, relationship_type=RelationshipType.USES.value)
    )
    success = service.delete_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_id=edge.id)
    assert success is True
    assert service.get_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_id=edge.id) is None

# =========================================================
# 3. Neighbors & Traversal Tests
# =========================================================

def test_neighbor_lookup(db):
    service = KnowledgeGraphService(db)
    center = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Center"))
    out_node = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.DOCUMENT.value, name="Doc"))
    in_node = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.USER.value, name="User"))

    service.create_edge(
        user_id=USER_A_ID, workspace_id=WS_A_ID,
        edge_data=EdgeCreate(source_node_id=center.id, target_node_id=out_node.id, relationship_type=RelationshipType.CONTAINS.value)
    )
    service.create_edge(
        user_id=USER_A_ID, workspace_id=WS_A_ID,
        edge_data=EdgeCreate(source_node_id=in_node.id, target_node_id=center.id, relationship_type=RelationshipType.OWNS.value)
    )

    both = service.get_neighbors(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=center.id, direction="both")
    assert len(both) == 2

    out_only = service.get_neighbors(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=center.id, direction="outgoing")
    assert len(out_only) == 1
    assert out_only[0]["node"].id == out_node.id

    in_only = service.get_neighbors(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=center.id, direction="incoming")
    assert len(in_only) == 1
    assert in_only[0]["node"].id == in_node.id

def test_graph_traversal_bfs(db):
    service = KnowledgeGraphService(db)
    # A -> B -> C
    a = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="A"))
    b = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.TASK.value, name="B"))
    c = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="C"))

    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=a.id, target_node_id=b.id, relationship_type=RelationshipType.CONTAINS.value))
    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=b.id, target_node_id=c.id, relationship_type=RelationshipType.ASSIGNED_TO.value))

    res = service.traverse(user_id=USER_A_ID, workspace_id=WS_A_ID, start_node_ids=[a.id], max_depth=2)
    assert res["total_nodes"] == 3
    assert res["total_edges"] == 2
    assert res["depth_reached"] == 2

def test_graph_traversal_cycle_handling(db):
    service = KnowledgeGraphService(db)
    # Cycle: A -> B -> C -> A
    a = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="A"))
    b = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.TASK.value, name="B"))
    c = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="C"))

    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=a.id, target_node_id=b.id, relationship_type=RelationshipType.DEPENDS_ON.value))
    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=b.id, target_node_id=c.id, relationship_type=RelationshipType.DEPENDS_ON.value))
    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=c.id, target_node_id=a.id, relationship_type=RelationshipType.DEPENDS_ON.value))

    res = service.traverse(user_id=USER_A_ID, workspace_id=WS_A_ID, start_node_ids=[a.id], max_depth=5)
    assert res["total_nodes"] == 3
    assert res["total_edges"] == 3

def test_graph_traversal_depth_limits(db):
    service = KnowledgeGraphService(db)
    # Chain of 6 nodes: N0 -> N1 -> N2 -> N3 -> N4 -> N5
    nodes = [
        service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.TASK.value, name=f"Node {i}"))
        for i in range(6)
    ]
    for i in range(5):
        service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=nodes[i].id, target_node_id=nodes[i+1].id, relationship_type=RelationshipType.DEPENDS_ON.value))

    # Max depth requested 2 -> should only reach N0, N1, N2
    res = service.traverse(user_id=USER_A_ID, workspace_id=WS_A_ID, start_node_ids=[nodes[0].id], max_depth=2)
    assert res["total_nodes"] == 3
    assert res["depth_reached"] == 2

# =========================================================
# 4. Filtering, Pagination & Search Tests
# =========================================================

def test_pagination(db):
    service = KnowledgeGraphService(db)
    for i in range(15):
        service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.TASK.value, name=f"Task {i}"))

    nodes, total = service.list_nodes(user_id=USER_A_ID, workspace_id=WS_A_ID, skip=5, limit=5)
    assert total == 15
    assert len(nodes) == 5

def test_node_type_filtering(db):
    service = KnowledgeGraphService(db)
    service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.SKILL.value, name="Skill 1"))
    service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.DOCUMENT.value, name="Doc 1"))

    skills, count = service.list_nodes(user_id=USER_A_ID, workspace_id=WS_A_ID, node_type=NodeType.SKILL.value)
    assert count == 1
    assert skills[0].name == "Skill 1"

def test_relationship_type_filtering(db):
    service = KnowledgeGraphService(db)
    n1 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="Agent"))
    n2 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.SKILL.value, name="Skill"))
    n3 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.TASK.value, name="Task"))

    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=n1.id, target_node_id=n2.id, relationship_type=RelationshipType.USES.value))
    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=n1.id, target_node_id=n3.id, relationship_type=RelationshipType.WORKS_ON.value))

    edges, total = service.list_edges(user_id=USER_A_ID, workspace_id=WS_A_ID, relationship_type=RelationshipType.USES.value)
    assert total == 1
    assert edges[0].relationship_type == "USES"

def test_node_search(db):
    service = KnowledgeGraphService(db)
    service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Quantum Computing Initiative", description="Quantum circuits"))
    service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Database Optimization", description="PostgreSQL tuning"))

    results = service.search_nodes(user_id=USER_A_ID, workspace_id=WS_A_ID, query="Quantum")
    assert len(results) == 1
    assert results[0].name == "Quantum Computing Initiative"

# =========================================================
# 5. Tenant Isolation & Security Tests
# =========================================================

def test_tenant_isolation_cross_workspace_node(db):
    service = KnowledgeGraphService(db)
    node_b = service.create_node(user_id=USER_B_ID, workspace_id=WS_B_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Confidential Project B"))

    # User A tries to read Node B
    retrieved = service.get_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=node_b.id)
    assert retrieved is None

def test_tenant_isolation_cross_user_node(db):
    service = KnowledgeGraphService(db)
    node_a = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.DOCUMENT.value, name="Secret Document A"))

    # User B in WS B tries to fetch node_a
    retrieved = service.get_node(user_id=USER_B_ID, workspace_id=WS_B_ID, node_id=node_a.id)
    assert retrieved is None

def test_cross_tenant_edge_rejection(db):
    service = KnowledgeGraphService(db)
    node_a = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node A"))
    node_b = service.create_node(user_id=USER_B_ID, workspace_id=WS_B_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node B"))

    # User A attempts to connect Node A to Node B
    with pytest.raises(NodeNotFound):
        service.create_edge(
            user_id=USER_A_ID,
            workspace_id=WS_A_ID,
            edge_data=EdgeCreate(source_node_id=node_a.id, target_node_id=node_b.id, relationship_type=RelationshipType.RELATED_TO.value)
        )

def test_cross_tenant_update_rejection(db):
    service = KnowledgeGraphService(db)
    node_b = service.create_node(user_id=USER_B_ID, workspace_id=WS_B_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node B"))

    # User A attempts to update Node B
    with pytest.raises(NodeNotFound):
        service.update_node(
            user_id=USER_A_ID,
            workspace_id=WS_A_ID,
            node_id=node_b.id,
            update_data=NodeUpdate(name="Tampered Name")
        )

def test_cross_tenant_delete_rejection(db):
    service = KnowledgeGraphService(db)
    node_b = service.create_node(user_id=USER_B_ID, workspace_id=WS_B_ID, node_data=NodeCreate(node_type=NodeType.PROJECT.value, name="Node B"))

    # User A attempts to delete Node B
    with pytest.raises(NodeNotFound):
        service.delete_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_id=node_b.id)

def test_duplicate_edge_rejection(db):
    service = KnowledgeGraphService(db)
    n1 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.AGENT.value, name="A1"))
    n2 = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.SKILL.value, name="S1"))

    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=n1.id, target_node_id=n2.id, relationship_type=RelationshipType.USES.value))

    with pytest.raises(DuplicateEdgeError):
        service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=n1.id, target_node_id=n2.id, relationship_type=RelationshipType.USES.value))

def test_metadata_size_validation():
    large_payload = {"key": "x" * 70000}
    with pytest.raises(ValidationError):
        NodeCreate(node_type=NodeType.DOCUMENT.value, name="Doc", metadata=large_payload)

def test_malformed_node_type_rejection():
    with pytest.raises(ValidationError):
        NodeCreate(node_type="INVALID_TYPE", name="Bad Node")

def test_malformed_relationship_type_rejection():
    with pytest.raises(ValidationError):
        EdgeCreate(source_node_id=uuid.uuid4(), target_node_id=uuid.uuid4(), relationship_type="INVALID_REL")

# =========================================================
# 6. Integration Helpers & RAG Tests
# =========================================================

def test_sync_document_graph_helper(db):
    service = KnowledgeGraphService(db)
    doc = Document(
        id=uuid.uuid4(),
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        filename="quarterly_report.pdf",
        original_filename="quarterly_report.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="chk_123",
        storage_path="/storage/quarterly_report.pdf"
    )
    db.add(doc)
    db.commit()

    chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=USER_A_ID,
        workspace_id=WS_A_ID,
        chunk_index=0,
        content="Revenue grew by 25% YoY.",
        content_hash="hash_chunk_1",
        token_count=10,
        character_count=24,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536
    )
    db.add(chunk_1)
    db.commit()

    doc.chunks = [chunk_1]

    nodes = service.sync_document_graph(doc)
    assert len(nodes) >= 2  # Doc node and Chunk node

    doc_node = next(n for n in nodes if n.node_type == NodeType.DOCUMENT.value)
    assert doc_node.name == "quarterly_report.pdf"

    chunk_node = next(n for n in nodes if n.node_type == NodeType.DOCUMENT_CHUNK.value)
    assert "Chunk 0" in chunk_node.name

    # Check edges
    edges, total = service.list_edges(user_id=USER_A_ID, workspace_id=WS_A_ID, source_node_id=doc_node.id)
    assert total >= 3  # BELONGS_TO Workspace, CREATED_BY User, CONTAINS Chunk

def test_rag_graph_context_retrieval(db):
    service = KnowledgeGraphService(db)
    doc_node = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.DOCUMENT.value, name="API_Spec.md", description="REST API Documentation"))
    user_node = service.create_node(user_id=USER_A_ID, workspace_id=WS_A_ID, node_data=NodeCreate(node_type=NodeType.USER.value, name="Alice", description="Lead Engineer"))
    
    service.create_edge(user_id=USER_A_ID, workspace_id=WS_A_ID, edge_data=EdgeCreate(source_node_id=doc_node.id, target_node_id=user_node.id, relationship_type=RelationshipType.CREATED_BY.value))

    ctx = service.get_graph_context(user_id=USER_A_ID, workspace_id=WS_A_ID, node_ids=[doc_node.id], max_depth=1)
    assert len(ctx["entities"]) == 2
    assert len(ctx["relationships"]) == 1
    assert "Knowledge Graph Entities:" in ctx["formatted_context"]
    assert "API_Spec.md" in ctx["formatted_context"]
    assert "Alice" in ctx["formatted_context"]
    assert "CREATED_BY" in ctx["formatted_context"]

# =========================================================
# 7. REST API Integration Tests
# =========================================================

def test_api_endpoints_crud_and_traversal(client):
    # 1. Create Node
    res = client.post("/api/v1/knowledge-graph/nodes", json={"node_type": "PROJECT", "name": "Apollo Mission"})
    assert res.status_code == 201
    node_1 = res.json()
    n1_id = node_1["id"]

    # 2. Create second node
    res = client.post("/api/v1/knowledge-graph/nodes", json={"node_type": "AGENT", "name": "Commander Agent"})
    assert res.status_code == 201
    node_2 = res.json()
    n2_id = node_2["id"]

    # 3. Create Edge
    res = client.post("/api/v1/knowledge-graph/edges", json={
        "source_node_id": n1_id,
        "target_node_id": n2_id,
        "relationship_type": "ASSIGNED_TO",
        "confidence": 1.0
    })
    assert res.status_code == 201
    edge = res.json()
    edge_id = edge["id"]

    # 4. Get Node
    res = client.get(f"/api/v1/knowledge-graph/nodes/{n1_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Apollo Mission"

    # 5. List Nodes
    res = client.get("/api/v1/knowledge-graph/nodes")
    assert res.status_code == 200
    assert len(res.json()) >= 2

    # 6. Get Neighbors
    res = client.get(f"/api/v1/knowledge-graph/nodes/{n1_id}/neighbors")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 7. Traverse
    res = client.post("/api/v1/knowledge-graph/traverse", json={
        "start_node_ids": [n1_id],
        "max_depth": 2
    })
    assert res.status_code == 200
    assert res.json()["total_nodes"] == 2

    # 8. Search
    res = client.get("/api/v1/knowledge-graph/search?q=Apollo")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 9. Delete Edge
    res = client.delete(f"/api/v1/knowledge-graph/edges/{edge_id}")
    assert res.status_code == 204

    # 10. Delete Node
    res = client.delete(f"/api/v1/knowledge-graph/nodes/{n1_id}")
    assert res.status_code == 204
