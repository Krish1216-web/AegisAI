import pytest
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.entity_extraction.resolver import EntityResolver, ResolutionResult
from app.services.entity_extraction.models import ExtractedEntity
from app.services.entity_extraction.normalizer import EntityNormalizer

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

    # Seed Org & Role
    org = Organization(id=uuid.uuid4(), name="Resolution Test Org")
    session.add(org)
    role = Role(id=uuid.uuid4(), name="member")
    session.add(role)
    session.commit()

    # Seed User 1 (Tenant 1) & Workspace 1
    u1 = User(id=uuid.UUID("11111111-1111-1111-1111-111111111111"), email="u1@aegis.ai", username="u1", password_hash="h", role_id=role.id)
    ws1 = Workspace(id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), organization_id=org.id, name="WS 1")
    session.add_all([u1, ws1])

    # Seed User 2 (Tenant 2) & Workspace 2
    u2 = User(id=uuid.UUID("22222222-2222-2222-2222-222222222222"), email="u2@aegis.ai", username="u2", password_hash="h", role_id=role.id)
    ws2 = Workspace(id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), organization_id=org.id, name="WS 2")
    session.add_all([u2, ws2])

    session.commit()

    try:
        yield session
    finally:
        session.close()

def test_exact_canonical_match(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    resolver = EntityResolver(db_session)

    # Pre-create node
    node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="PostgreSQL",
        node_type=NodeType.SKILL.value,
        description="SQL Database"
    )
    db_session.add(node)
    db_session.commit()

    # Resolve mention
    ent = ExtractedEntity(name="postgresql", entity_type="SKILL")
    matched_node, res = resolver.resolve_entity(u1, ws1, ent)

    assert matched_node is not None
    assert matched_node.id == node.id
    assert res.matched is True
    assert res.strategy == "exact"
    assert res.confidence == 1.0

def test_alias_match(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    resolver = EntityResolver(db_session)

    node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="Kubernetes",
        node_type=NodeType.SKILL.value
    )
    db_session.add(node)
    db_session.commit()

    ent = ExtractedEntity(name="k8s", entity_type="SKILL")
    matched_node, res = resolver.resolve_entity(u1, ws1, ent)

    assert matched_node is not None
    assert matched_node.id == node.id
    assert res.strategy == "alias"
    assert res.confidence >= 0.95

def test_type_aware_mismatch_prevention(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    resolver = EntityResolver(db_session)

    # Node is a TASK
    node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="AegisAI",
        node_type=NodeType.TASK.value
    )
    db_session.add(node)
    db_session.commit()

    # Extracted entity is a SKILL
    ent = ExtractedEntity(name="AegisAI", entity_type="SKILL")
    matched_node, res = resolver.resolve_entity(u1, ws1, ent)

    # Must NOT merge incompatible types without explicit alias
    assert matched_node is None
    assert res.matched is False

def test_fuzzy_matching(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    resolver = EntityResolver(db_session)

    node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="Elasticsearch",
        node_type=NodeType.SKILL.value
    )
    db_session.add(node)
    db_session.commit()

    # Slight typo mention "ElasticSearchDB" or "Elasticsearhc"
    ent = ExtractedEntity(name="Elasticsearhc", entity_type="SKILL")
    matched_node, res = resolver.resolve_entity(u1, ws1, ent, allow_fuzzy=True, fuzzy_threshold=0.85)

    assert matched_node is not None
    assert matched_node.id == node.id
    assert res.strategy == "fuzzy"
    assert res.confidence >= 0.85

def test_duplicate_prevention_on_repeated_resolution(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    resolver = EntityResolver(db_session)

    ent = ExtractedEntity(name="FastAPI", entity_type="SKILL", description="API framework", chunk_id=uuid.uuid4())
    
    # 1. First resolution creates node
    node1 = resolver.resolve_or_create_node(u1, ws1, ent)
    assert node1.name == "FastAPI"

    # 2. Second resolution from another chunk resolves to node1
    chunk_id_2 = uuid.uuid4()
    ent2 = ExtractedEntity(name="fast-api", entity_type="SKILL", chunk_id=chunk_id_2)
    node2 = resolver.resolve_or_create_node(u1, ws1, ent2)

    assert node2.id == node1.id
    # Provenance list should contain both chunk IDs
    prov = node2.meta_data.get("provenance", [])
    assert len(prov) == 2

    # Total nodes in DB should still be 1
    total = db_session.query(KnowledgeGraphNode).filter(KnowledgeGraphNode.workspace_id == ws1).count()
    assert total == 1

def test_tenant_isolation_in_resolution(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    u2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ws2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    resolver = EntityResolver(db_session)

    # Node in WS 1
    node1 = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="PrivateAlphaProject",
        node_type=NodeType.PROJECT.value
    )
    db_session.add(node1)
    db_session.commit()

    # User 2 in WS 2 tries to resolve "PrivateAlphaProject"
    ent = ExtractedEntity(name="PrivateAlphaProject", entity_type="PROJECT")
    matched_node, res = resolver.resolve_entity(u2, ws2, ent)

    # Must be completely isolated
    assert matched_node is None
    assert res.matched is False

def test_safe_merge_duplicate_nodes(db_session):
    u1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ws1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    resolver = EntityResolver(db_session)

    target_node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="PostgreSQL",
        node_type=NodeType.SKILL.value,
        meta_data={"aliases": ["postgres"]}
    )
    source_node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="Postgres DB",
        node_type=NodeType.SKILL.value,
        meta_data={"aliases": ["pgsql"]}
    )
    other_node = KnowledgeGraphNode(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        name="AegisAI",
        node_type=NodeType.PROJECT.value
    )
    db_session.add_all([target_node, source_node, other_node])
    db_session.commit()

    # Edge from other_node to source_node
    edge = KnowledgeGraphEdge(
        id=uuid.uuid4(),
        user_id=u1,
        workspace_id=ws1,
        source_node_id=other_node.id,
        target_node_id=source_node.id,
        relationship_type=RelationshipType.USES.value,
        confidence=0.9
    )
    db_session.add(edge)
    db_session.commit()

    # Merge source into target
    merged = resolver.merge_duplicate_nodes(u1, ws1, source_node.id, target_node.id)

    assert merged is not None
    assert merged.id == target_node.id
    # Source node deleted
    assert db_session.query(KnowledgeGraphNode).filter(KnowledgeGraphNode.id == source_node.id).first() is None
    # Edge rerouted to target_node
    db_session.refresh(edge)
    assert edge.target_node_id == target_node.id
    # Aliases merged
    assert "Postgres DB" in merged.meta_data.get("aliases", [])
