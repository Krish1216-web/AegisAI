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
    WorkflowUpdate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowVariableCreate
)
from app.services.workflow import WorkflowService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Workflow Svc Org")
    role = Role(id=uuid.uuid4(), name="Admin")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Svc")
    user = User(id=uuid.uuid4(), email="admin@svc.com", username="svcadmin", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_workflow_crud_and_versioning(db_session: Session, test_setup):
    svc = WorkflowService(db_session)
    u_id = test_setup["user"].id
    ws_id = test_setup["ws"].id

    # 1. Create Workflow
    create_payload = WorkflowCreate(
        name="Data Enrichment",
        description="Version 1 pipeline",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", config={}),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", config={})
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")
        ],
        variables=[
            WorkflowVariableCreate(name="max_retries", value="3", value_type="number")
        ]
    )
    wf = svc.create_workflow(u_id, ws_id, create_payload)
    assert wf.version == 1
    assert wf.status == WorkflowStatus.DRAFT
    assert len(wf.nodes) == 2
    assert len(wf.edges) == 1

    # 2. Update structural components -> Version increments
    update_payload = WorkflowUpdate(
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", config={}),
            WorkflowNodeCreate(node_key="t1", node_type=WorkflowNodeType.TRANSFORM, name="Transform", config={}),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", config={})
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="s1", target_node_key="t1"),
            WorkflowEdgeCreate(source_node_key="t1", target_node_key="e1")
        ]
    )
    updated = svc.update_workflow(u_id, ws_id, wf.id, update_payload)
    assert updated.version == 2
    assert len(updated.nodes) == 3
    assert len(updated.edges) == 2

    # 3. Non-structural update (just name/description) -> Version unchanged
    non_struct = svc.update_workflow(u_id, ws_id, wf.id, WorkflowUpdate(description="Updated description only"))
    assert non_struct.version == 2
    assert non_struct.description == "Updated description only"

def test_workflow_activation_lifecycle(db_session: Session, test_setup):
    svc = WorkflowService(db_session)
    u_id = test_setup["user"].id
    ws_id = test_setup["ws"].id

    create_payload = WorkflowCreate(
        name="Lifecycle Pipeline",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", config={}),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", config={})
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")
        ]
    )
    wf = svc.create_workflow(u_id, ws_id, create_payload)

    # 1. Activate
    active_wf, val = svc.activate_workflow(u_id, ws_id, wf.id)
    assert active_wf is not None
    assert active_wf.status == WorkflowStatus.ACTIVE
    assert active_wf.is_active is True

    # 2. Pause
    paused_wf = svc.pause_workflow(u_id, ws_id, wf.id)
    assert paused_wf.status == WorkflowStatus.PAUSED
    assert paused_wf.is_active is False

    # 3. Archive
    archived_wf = svc.archive_workflow(u_id, ws_id, wf.id)
    assert archived_wf.status == WorkflowStatus.ARCHIVED

    # 4. Soft delete
    deleted = svc.delete_workflow(u_id, ws_id, wf.id)
    assert deleted is True
    assert svc.get_workflow(u_id, ws_id, wf.id) is None
