import pytest
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.graph_analytics import GraphAnalyticsService
from app.schemas.knowledge_graph import AdvancedSearchRequest

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

    org = Organization(id=uuid.uuid4(), name="Analytics Test Org")
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

def test_graph_analytics_overview(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = GraphAnalyticsService(db_session)

    n1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="AegisAI", node_type="PROJECT")
    n2 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="FastAPI", node_type="SKILL")
    n3 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="OrphanNode", node_type="DOCUMENT")
    db_session.add_all([n1, n2, n3])
    db_session.commit()

    e1 = KnowledgeGraphEdge(
        id=uuid.uuid4(), user_id=u1, workspace_id=ws1,
        source_node_id=n1.id, target_node_id=n2.id,
        relationship_type="USES", confidence=0.95
    )
    db_session.add(e1)
    db_session.commit()

    overview = service.get_analytics_overview(u1, ws1)
    assert overview.total_nodes == 3
    assert overview.total_edges == 1
    assert overview.connected_nodes_count == 2
    assert overview.isolated_nodes_count == 1
    assert overview.nodes_by_type.get("PROJECT") == 1
    assert overview.edges_by_type.get("USES") == 1
    assert overview.average_confidence == 0.95

def test_graph_health_report(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = GraphAnalyticsService(db_session)

    # Empty graph health
    empty_health = service.get_graph_health(u1, ws1)
    assert empty_health.status == "HEALTHY"

    # Add isolated node and low-confidence edge with conflict
    n1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Node1", node_type="SKILL")
    n2 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Node2", node_type="SKILL")
    db_session.add_all([n1, n2])
    db_session.commit()

    e1 = KnowledgeGraphEdge(
        id=uuid.uuid4(), user_id=u1, workspace_id=ws1,
        source_node_id=n1.id, target_node_id=n2.id,
        relationship_type="CONTAINS", confidence=0.40,
        meta_data={"conflict_indicators": ["circular_containment"]}
    )
    db_session.add(e1)
    db_session.commit()

    health = service.get_graph_health(u1, ws1)
    assert health.status == "WARNING"
    assert health.low_confidence_edges_count >= 1
    assert health.conflicts_count >= 1

def test_top_connected_and_orphan_entities(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = GraphAnalyticsService(db_session)

    hub = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Hub", node_type="PROJECT")
    leaf1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Leaf1", node_type="SKILL")
    leaf2 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Leaf2", node_type="SKILL")
    orphan = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Orphan", node_type="TASK")
    db_session.add_all([hub, leaf1, leaf2, orphan])
    db_session.commit()

    e1 = KnowledgeGraphEdge(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, source_node_id=hub.id, target_node_id=leaf1.id, relationship_type="USES", confidence=0.9)
    e2 = KnowledgeGraphEdge(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, source_node_id=hub.id, target_node_id=leaf2.id, relationship_type="USES", confidence=0.9)
    db_session.add_all([e1, e2])
    db_session.commit()

    # Hub has degree 2
    top = service.get_top_connected_entities(u1, ws1, limit=5)
    assert len(top) == 4
    assert top[0].name == "Hub"
    assert top[0].degree == 2

    # Orphan detection
    orphans = service.get_orphan_nodes(u1, ws1, limit=10)
    assert len(orphans) == 1
    assert orphans[0].name == "Orphan"

def test_duplicate_candidate_detection(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = GraphAnalyticsService(db_session)

    # Similar names of same entity type
    n1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="PostgreSQL Database", node_type="SKILL")
    n2 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="PostgreSQL Databases", node_type="SKILL")
    n3 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Kubernetes Engine", node_type="SKILL")
    db_session.add_all([n1, n2, n3])
    db_session.commit()

    duplicates = service.detect_duplicate_candidates(u1, ws1, similarity_threshold=0.85)
    assert len(duplicates) >= 1
    assert "PostgreSQL" in duplicates[0].source_name
    assert duplicates[0].similarity_score >= 0.85

def test_advanced_search_ranking(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    service = GraphAnalyticsService(db_session)

    n_exact = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Python", node_type="SKILL", description="Primary backend language")
    n_prefix = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Python AsyncIO", node_type="SKILL", description="Concurrency runtime")
    n_desc = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="Django", node_type="PROJECT", description="Built using Python framework")
    db_session.add_all([n_exact, n_prefix, n_desc])
    db_session.commit()

    res = service.advanced_search(u1, ws1, AdvancedSearchRequest(query="Python", limit=10))
    assert res.total_matched >= 3
    # Exact match must rank highest
    assert res.results[0].node.name == "Python"
    assert res.results[0].match_type == "exact"
    # Prefix match must rank second
    assert res.results[1].node.name == "Python AsyncIO"
    assert res.results[1].match_type == "prefix"

def test_tenant_isolation_in_analytics(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ws2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    service = GraphAnalyticsService(db_session)

    # Add node to ws1
    n_ws1 = KnowledgeGraphNode(id=uuid.uuid4(), user_id=u1, workspace_id=ws1, name="WS1 Secret Project", node_type="PROJECT")
    db_session.add(n_ws1)
    db_session.commit()

    # Query analytics for ws2
    overview_ws2 = service.get_analytics_overview(u2, ws2)
    assert overview_ws2.total_nodes == 0
    assert overview_ws2.total_edges == 0

    search_ws2 = service.advanced_search(u2, ws2, AdvancedSearchRequest(query="Secret"))
    assert search_ws2.total_matched == 0
