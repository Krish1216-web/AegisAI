import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    WorkflowNodeType,
    WorkflowExecutionStatus
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate
)
from app.services.workflow import WorkflowService
from app.services.workflow_execution import WorkflowExecutionService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def fan_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Fan Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Fan")
    user = User(id=uuid.uuid4(), email="fan_user@test.com", username="fan_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_parallel_fanout_and_merge_fanin(db_session: Session, fan_setup):
    user = fan_setup["user"]
    ws = fan_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Graph:
    # START -> PARALLEL -> (BRANCH_A, BRANCH_B) -> MERGE -> END
    wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Fanout Fanin Pipeline",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="par_1", node_type=WorkflowNodeType.PARALLEL, name="Fan Out", config={"max_concurrency": 5}),
                WorkflowNodeCreate(
                    node_key="branch_a",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Branch A",
                    config={"mapping": {"score_a": 100}}
                ),
                WorkflowNodeCreate(
                    node_key="branch_b",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Branch B",
                    config={"mapping": {"score_b": 200}}
                ),
                WorkflowNodeCreate(
                    node_key="merge_1",
                    node_type=WorkflowNodeType.MERGE,
                    name="Merge In",
                    config={"policy": "all", "merge_key": "aggregated"}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="par_1"),
                WorkflowEdgeCreate(source_node_key="par_1", target_node_key="branch_a"),
                WorkflowEdgeCreate(source_node_key="par_1", target_node_key="branch_b"),
                WorkflowEdgeCreate(source_node_key="branch_a", target_node_key="merge_1"),
                WorkflowEdgeCreate(source_node_key="branch_b", target_node_key="merge_1"),
                WorkflowEdgeCreate(source_node_key="merge_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(user.id, ws.id, wf.id, input_data={"init": "start"})
    assert execution.status == WorkflowExecutionStatus.COMPLETED

    # Check execution nodes
    exec_nodes = {en.node_key: en for en in execution.execution_nodes}
    assert "par_1" in exec_nodes
    assert "branch_a" in exec_nodes
    assert "branch_b" in exec_nodes
    assert "merge_1" in exec_nodes

    merge_output = exec_nodes["merge_1"].output_data
    assert merge_output["policy"] == "all"
    assert "aggregated" in merge_output
    assert "branch_a" in merge_output["aggregated"]
    assert "branch_b" in merge_output["aggregated"]
