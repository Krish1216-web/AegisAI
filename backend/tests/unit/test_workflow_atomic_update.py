import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowNodeType
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowDefinitionUpdate
)
from app.services.workflow import WorkflowService, WorkflowArchivedError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def atomic_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Atomic Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Atomic")
    user = User(id=uuid.uuid4(), email="atomic_user@test.com", username="atom1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    svc = WorkflowService(db_session)
    wf = svc.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Pristine Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
        )
    )

    return {"user": user, "ws": ws, "wf": wf}

def test_atomic_rollback_on_invalid_graph_update(db_session: Session, atomic_setup):
    svc = WorkflowService(db_session)
    u = atomic_setup["user"]
    ws = atomic_setup["ws"]
    wf = atomic_setup["wf"]

    # Attempt to update with a cyclic graph (A -> B -> A)
    invalid_payload = WorkflowDefinitionUpdate(
        expected_version=1,
        name="Attempted Invalid Graph",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
            WorkflowNodeCreate(node_key="node_a", node_type=WorkflowNodeType.TRANSFORM, name="Node A"),
            WorkflowNodeCreate(node_key="node_b", node_type=WorkflowNodeType.TRANSFORM, name="Node B"),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="s1", target_node_key="node_a"),
            WorkflowEdgeCreate(source_node_key="node_a", target_node_key="node_b"),
            WorkflowEdgeCreate(source_node_key="node_b", target_node_key="node_a"),  # CYCLE
            WorkflowEdgeCreate(source_node_key="node_b", target_node_key="e1")
        ]
    )

    with pytest.raises(ValueError, match="cycle or loop"):
        svc.update_workflow_definition(u.id, ws.id, wf.id, invalid_payload)

    # Verify original workflow remains pristine
    pristine = svc.get_workflow_definition(u.id, ws.id, wf.id)
    assert pristine.version == 1
    assert pristine.name == "Pristine Workflow"
    assert len(pristine.nodes) == 2
    assert len(pristine.edges) == 1

def test_archived_workflow_modification_rejection(db_session: Session, atomic_setup):
    svc = WorkflowService(db_session)
    u = atomic_setup["user"]
    ws = atomic_setup["ws"]
    wf = atomic_setup["wf"]

    # Archive workflow
    svc.archive_workflow(u.id, ws.id, wf.id)

    payload = WorkflowDefinitionUpdate(
        expected_version=1,
        name="Modify Archived Graph",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
        ],
        edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
    )

    with pytest.raises(WorkflowArchivedError, match="Cannot modify archived workflow"):
        svc.update_workflow_definition(u.id, ws.id, wf.id, payload)
