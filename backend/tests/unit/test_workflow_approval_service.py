import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowNodeType,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowApprovalStatus,
    WorkflowApprovalPolicy,
    WorkflowApprovalRequest
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate
)
from app.services.workflow import WorkflowService
from app.services.workflow_execution import WorkflowExecutionService
from app.services.workflow_approval import WorkflowApprovalService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def approval_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Gov Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    user_role = Role(id=uuid.uuid4(), name="user")
    db_session.add_all([org, admin_role, user_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Gov")
    requester = User(id=uuid.uuid4(), email="requester@test.com", username="req_user", password_hash="pw", role_id=user_role.id, is_active=True)
    approver = User(id=uuid.uuid4(), email="approver@test.com", username="appr_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, requester, approver])
    db_session.flush()

    mem1 = WorkspaceMember(workspace_id=ws.id, user_id=requester.id, role="member")
    mem2 = WorkspaceMember(workspace_id=ws.id, user_id=approver.id, role="admin")
    db_session.add_all([mem1, mem2])
    db_session.commit()

    return {"requester": requester, "approver": approver, "ws": ws}

def test_approval_lifecycle_creation_and_resumption(db_session: Session, approval_setup):
    req_user = approval_setup["requester"]
    appr_user = approval_setup["approver"]
    ws = approval_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    appr_service = WorkflowApprovalService(db_session)

    # Workflow: START -> HUMAN_APPROVAL -> END
    wf = wf_service.create_workflow(
        req_user.id,
        ws.id,
        WorkflowCreate(
            name="Prod Deploy Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Security Gate",
                    config={
                        "title": "Production Deployment Signoff",
                        "approval_message": "Sign off release v2.0",
                        "approver_roles": ["admin"],
                        "requester_can_approve": False
                    }
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Deployment Executed Successfully"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    # 1. Execute -> pauses in WAITING and creates persistent WorkflowApprovalRequest
    execution = exec_service.execute_workflow(req_user.id, ws.id, wf.id, input_data={"release": "v2.0"})
    assert execution.status == WorkflowExecutionStatus.WAITING

    # Verify persistent approval request
    approvals, total = appr_service.list_approvals(ws.id, status="pending")
    assert total == 1
    approval = approvals[0]
    assert approval.title == "Production Deployment Signoff"
    assert approval.status == WorkflowApprovalStatus.PENDING
    assert approval.requested_by == req_user.id
    assert approval.requester_can_approve is False

    # 2. Approver grants approval -> Resumes workflow to COMPLETED
    decided = appr_service.approve(approval.id, ws.id, appr_user, reason="Verified QA metrics.")
    assert decided.status == WorkflowApprovalStatus.APPROVED
    assert decided.decided_by == appr_user.id
    assert len(decided.decision_history) == 1

    # Verify execution finished
    db_session.refresh(execution)
    assert execution.status == WorkflowExecutionStatus.COMPLETED

def test_approval_rejection_terminates_workflow(db_session: Session, approval_setup):
    req_user = approval_setup["requester"]
    appr_user = approval_setup["approver"]
    ws = approval_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    appr_service = WorkflowApprovalService(db_session)

    wf = wf_service.create_workflow(
        req_user.id,
        ws.id,
        WorkflowCreate(
            name="Rejectable Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Gate",
                    config={"title": "Signoff"}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(req_user.id, ws.id, wf.id)
    assert execution.status == WorkflowExecutionStatus.WAITING

    approvals, _ = appr_service.list_approvals(ws.id, status="pending")
    approval = approvals[0]

    # Reject
    rejected = appr_service.reject(approval.id, ws.id, appr_user, reason="Risk policy violation.")
    assert rejected.status == WorkflowApprovalStatus.REJECTED

    db_session.refresh(execution)
    assert execution.status == WorkflowExecutionStatus.FAILED
    assert "Human approval rejected" in str(execution.error)
