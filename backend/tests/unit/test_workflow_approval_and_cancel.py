import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowNodeType,
    WorkflowExecutionStatus,
    WorkflowNodeStatus
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
def appr_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Appr Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Appr")
    user = User(id=uuid.uuid4(), email="appr_user@test.com", username="appr1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_human_approval_pause_and_resume(db_session: Session, appr_setup):
    u = appr_setup["user"]
    ws = appr_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Workflow: START -> HUMAN_APPROVAL -> END
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Approval Gate Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Security Signoff",
                    config={"approval_message": "Please approve deployment to production"}
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Deployment approved and completed."}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    # 1. Execute workflow -> Pauses at HUMAN_APPROVAL
    execution = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        input_data={"deploy_target": "production"}
    )

    assert execution.status == WorkflowExecutionStatus.WAITING
    nodes_by_key = {en.node_key: en for en in execution.execution_nodes}
    assert nodes_by_key["appr_1"].status == WorkflowNodeStatus.WAITING

    # 2. Approve execution -> Resumes to completed
    resumed = exec_service.approve_execution(
        user_id=u.id,
        workspace_id=ws.id,
        execution_id=execution.id,
        approved=True
    )
    assert resumed.status == WorkflowExecutionStatus.COMPLETED

def test_execution_cancellation(db_session: Session, appr_setup):
    u = appr_setup["user"]
    ws = appr_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Cancelable Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Pause Gate"
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id
    )
    assert execution.status == WorkflowExecutionStatus.WAITING

    cancelled = exec_service.cancel_execution(
        user_id=u.id,
        workspace_id=ws.id,
        execution_id=execution.id
    )
    assert cancelled.status == WorkflowExecutionStatus.CANCELLED
