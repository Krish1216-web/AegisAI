import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    WorkflowNodeType,
    WorkflowApprovalStatus,
    WorkflowApprovalPolicy,
    WorkflowExecutionStatus
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
def policy_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Policy Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Policy")
    user1 = User(id=uuid.uuid4(), email="u1@test.com", username="approver_1", password_hash="pw", role_id=admin_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="u2@test.com", username="approver_2", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user1, user2])
    db_session.flush()

    mem1 = WorkspaceMember(workspace_id=ws.id, user_id=user1.id, role="admin")
    mem2 = WorkspaceMember(workspace_id=ws.id, user_id=user2.id, role="admin")
    db_session.add_all([mem1, mem2])
    db_session.commit()

    return {"u1": user1, "u2": user2, "ws": ws}

def test_multi_approver_policy_and_duplicate_prevention(db_session: Session, policy_setup):
    u1 = policy_setup["u1"]
    u2 = policy_setup["u2"]
    ws = policy_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    appr_service = WorkflowApprovalService(db_session)

    # Workflow requiring 2 approvals (required_count=2)
    wf = wf_service.create_workflow(
        u1.id,
        ws.id,
        WorkflowCreate(
            name="Dual Signoff WF",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Dual Gate",
                    config={
                        "required_count": 2,
                        "policy": "all_approvers",
                        "approver_roles": ["admin"],
                        "requester_can_approve": True
                    }
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(u1.id, ws.id, wf.id)
    approvals, _ = appr_service.list_approvals(ws.id, status="pending")
    approval = approvals[0]

    # 1. User 1 approves -> status remains PENDING (1/2)
    appr_service.approve(approval.id, ws.id, u1, reason="First signoff.")
    db_session.refresh(approval)
    assert approval.status == WorkflowApprovalStatus.PENDING
    assert len(approval.decision_history) == 1

    # 2. Duplicate decision from User 1 is rejected
    with pytest.raises(ValueError) as exc:
        appr_service.approve(approval.id, ws.id, u1, reason="Duplicate attempt")
    assert "already submitted an approval decision" in str(exc.value)

    # 3. User 2 approves -> status becomes APPROVED (2/2) & execution resumes
    appr_service.approve(approval.id, ws.id, u2, reason="Second signoff.")
    db_session.refresh(approval)
    assert approval.status == WorkflowApprovalStatus.APPROVED
    assert len(approval.decision_history) == 2

    db_session.refresh(execution)
    assert execution.status == WorkflowExecutionStatus.COMPLETED
