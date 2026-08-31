import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowNodeType
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowVariableCreate
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
def exec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Exec Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Exec")
    user = User(id=uuid.uuid4(), email="exec_user@test.com", username="exec1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    wf_svc = WorkflowService(db_session)
    create_payload = WorkflowCreate(
        name="Sequential Processing",
        nodes=[
            WorkflowNodeCreate(node_key="start_node", node_type=WorkflowNodeType.START, name="Start", config={}),
            WorkflowNodeCreate(
                node_key="format_node",
                node_type=WorkflowNodeType.TRANSFORM,
                name="Format Data",
                config={"mapping": {"formatted_name": "{{input.user_name}}", "env": "{{variables.stage}}"}}
            ),
            WorkflowNodeCreate(
                node_key="end_node",
                node_type=WorkflowNodeType.END,
                name="End Output",
                config={"output_template": "Processed: {{nodes.format_node.output.transformed.formatted_name}} (Env: {{nodes.format_node.output.transformed.env}})"}
            )
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="start_node", target_node_key="format_node", priority=1),
            WorkflowEdgeCreate(source_node_key="format_node", target_node_key="end_node", priority=1)
        ],
        variables=[
            WorkflowVariableCreate(name="stage", value="production", value_type="string")
        ]
    )
    wf = wf_svc.create_workflow(user.id, ws.id, create_payload)
    return {"user": user, "ws": ws, "workflow": wf}

def test_workflow_topological_execution(db_session: Session, exec_setup):
    exec_svc = WorkflowExecutionService(db_session)
    u = exec_setup["user"]
    ws = exec_setup["ws"]
    wf = exec_setup["workflow"]

    input_payload = {"user_name": "Alice Developer"}
    execution = exec_svc.execute_workflow(u.id, ws.id, wf.id, input_payload)

    assert execution.status == WorkflowExecutionStatus.COMPLETED
    assert execution.snapshot is not None
    assert execution.snapshot["version"] == wf.version
    assert len(execution.execution_nodes) == 3

    # Check node execution sequence
    keys = [n.node_key for n in execution.execution_nodes]
    assert keys == ["start_node", "format_node", "end_node"]

    # Verify output resolution
    assert "Alice Developer" in str(execution.output_data)
    assert "production" in str(execution.output_data)

def test_workflow_cancellation(db_session: Session, exec_setup):
    exec_svc = WorkflowExecutionService(db_session)
    u = exec_setup["user"]
    ws = exec_setup["ws"]
    wf = exec_setup["workflow"]

    # Create dummy pending execution
    from app.models.workflow import WorkflowExecution
    pending_exec = WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        user_id=u.id,
        workspace_id=ws.id,
        status=WorkflowExecutionStatus.PENDING,
        input_data={}
    )
    db_session.add(pending_exec)
    db_session.commit()

    cancelled = exec_svc.cancel_execution(u.id, ws.id, pending_exec.id)
    assert cancelled.status == WorkflowExecutionStatus.CANCELLED
    assert cancelled.completed_at is not None
