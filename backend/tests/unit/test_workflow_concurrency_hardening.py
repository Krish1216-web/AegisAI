import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    WorkflowNodeType,
    WorkflowExecutionStatus,
    WorkflowExecution
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
def conc_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Conc Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Conc")
    user = User(id=uuid.uuid4(), email="conc_user@test.com", username="conc_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_execution_idempotency_key(db_session: Session, conc_setup):
    """Verify that using the same idempotency key while an execution is running returns the same instance."""
    user = conc_setup["user"]
    ws = conc_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Idempotency Test",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="end_1")
            ]
        )
    )

    # Insert a dummy pending execution with a fixed idempotency key
    existing_exec = WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        workflow_version=1,
        user_id=user.id,
        workspace_id=ws.id,
        status=WorkflowExecutionStatus.RUNNING,
        started_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(existing_exec)
    db_session.commit()

    # Trigger with idempotency key
    exec_res = exec_service.execute_workflow(
        user.id,
        ws.id,
        wf.id,
        idempotency_key="key-abc-123"
    )

    assert exec_res.id == existing_exec.id

def test_fast_execution_cancellation(db_session: Session, conc_setup):
    """Verify cancelling an execution prevents downstream node processing."""
    user = conc_setup["user"]
    ws = conc_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Cancel Flow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Approval Gate",
                    config={"title": "Approve Deployment"}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    # Execute workflow -> pauses at human approval
    execution = exec_service.execute_workflow(user.id, ws.id, wf.id)
    assert execution.status == WorkflowExecutionStatus.WAITING

    # Cancel execution
    cancelled_exec = exec_service.cancel_execution(user.id, ws.id, execution.id, reason="User manual cancel")
    assert cancelled_exec.status == WorkflowExecutionStatus.CANCELLED
    assert "User manual cancel" in cancelled_exec.error
