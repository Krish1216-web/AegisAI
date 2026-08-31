import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowNodeType
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowDefinitionUpdate
)
from app.services.workflow import WorkflowService, VersionConflictError

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def conflict_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Conflict Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Conflict")
    user = User(id=uuid.uuid4(), email="conflict_user@test.com", username="conf1", password_hash="pw", role_id=role.id, is_active=True)
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
            name="Concurrent Graph",
            nodes=[
                WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
        )
    )

    return {"user": user, "ws": ws, "wf": wf}

def test_optimistic_concurrency_version_conflict(db_session: Session, conflict_setup):
    svc = WorkflowService(db_session)
    u = conflict_setup["user"]
    ws = conflict_setup["ws"]
    wf = conflict_setup["wf"]

    # Initial version is 1
    assert wf.version == 1

    # Session A updates with expected_version=1 -> succeeds and bumps to version 2
    payload_a = WorkflowDefinitionUpdate(
        expected_version=1,
        name="Session A Update",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
        ],
        edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
    )
    res_a = svc.update_workflow_definition(u.id, ws.id, wf.id, payload_a)
    assert res_a.version == 2

    # Session B attempts to update with stale expected_version=1 -> raises VersionConflictError
    payload_b = WorkflowDefinitionUpdate(
        expected_version=1,
        name="Session B Stale Update",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
        ],
        edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
    )
    with pytest.raises(VersionConflictError, match="Workflow version conflict"):
        svc.update_workflow_definition(u.id, ws.id, wf.id, payload_b)

    # Session B reloads latest version (2) and saves with expected_version=2 -> succeeds
    payload_b.expected_version = 2
    res_b = svc.update_workflow_definition(u.id, ws.id, wf.id, payload_b)
    assert res_b.version == 3
    assert res_b.name == "Session B Stale Update"
