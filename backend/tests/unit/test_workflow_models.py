import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowVariable,
    WorkflowExecution,
    WorkflowExecutionNode,
    WorkflowStatus,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowNodeType
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_workflow_models_crud(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Workflow Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Workflow")
    user = User(id=uuid.uuid4(), email="wf_user@test.com", username="wf1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    # 1. Create Workflow
    wf = Workflow(
        id=uuid.uuid4(),
        user_id=user.id,
        workspace_id=ws.id,
        name="Lead Processing Workflow",
        description="Automates lead enrichment and routing",
        status=WorkflowStatus.DRAFT,
        version=1,
        is_active=False
    )
    db_session.add(wf)
    db_session.flush()

    # 2. Create Nodes
    n_start = WorkflowNode(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        node_key="start_node",
        node_type=WorkflowNodeType.START,
        name="Start Trigger",
        config={"input_schema": {"type": "object"}},
        position={"x": 0, "y": 0}
    )
    n_end = WorkflowNode(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        node_key="end_node",
        node_type=WorkflowNodeType.END,
        name="End Output",
        config={"output_template": "Done"},
        position={"x": 200, "y": 0}
    )
    db_session.add_all([n_start, n_end])
    db_session.flush()

    # 3. Create Edge
    edge = WorkflowEdge(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        source_node_id=n_start.id,
        target_node_id=n_end.id,
        priority=1
    )
    db_session.add(edge)

    # 4. Create Variable
    var = WorkflowVariable(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        name="api_timeout",
        value="30",
        value_type="number",
        is_secret=False
    )
    db_session.add(var)

    # 5. Create Execution & ExecutionNode
    exec_rec = WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        workflow_version=1,
        user_id=user.id,
        workspace_id=ws.id,
        status=WorkflowExecutionStatus.PENDING,
        input_data={"lead_email": "test@lead.com"}
    )
    db_session.add(exec_rec)
    db_session.flush()

    exec_node = WorkflowExecutionNode(
        id=uuid.uuid4(),
        execution_id=exec_rec.id,
        node_id=n_start.id,
        node_key="start_node",
        status=WorkflowNodeStatus.COMPLETED,
        output_data={"status": "OK"}
    )
    db_session.add(exec_node)
    db_session.commit()

    # Verification
    saved_wf = db_session.query(Workflow).filter(Workflow.id == wf.id).first()
    assert saved_wf is not None
    assert len(saved_wf.nodes) == 2
    assert len(saved_wf.edges) == 1
    assert len(saved_wf.variables) == 1
    assert len(saved_wf.executions) == 1
    assert saved_wf.executions[0].execution_nodes[0].node_key == "start_node"
