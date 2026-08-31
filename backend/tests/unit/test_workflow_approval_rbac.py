import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    WorkflowNodeType,
    WorkflowApprovalStatus
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
def rbac_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="RBAC Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    member_role = Role(id=uuid.uuid4(), name="member")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, member_role, viewer_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS RBAC")
    requester = User(id=uuid.uuid4(), email="req@test.com", username="req", password_hash="pw", role_id=member_role.id, is_active=True)
    viewer = User(id=uuid.uuid4(), email="view@test.com", username="view", password_hash="pw", role_id=viewer_role.id, is_active=True)
    admin = User(id=uuid.uuid4(), email="admin@test.com", username="adm", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, requester, viewer, admin])
    db_session.flush()

    mem1 = WorkspaceMember(workspace_id=ws.id, user_id=requester.id, role="member")
    mem2 = WorkspaceMember(workspace_id=ws.id, user_id=viewer.id, role="viewer")
    mem3 = WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="admin")
    db_session.add_all([mem1, mem2, mem3])
    db_session.commit()

    return {"requester": requester, "viewer": viewer, "admin": admin, "ws": ws}

def test_self_approval_separation_policy(db_session: Session, rbac_setup):
    req_user = rbac_setup["requester"]
    adm_user = rbac_setup["admin"]
    ws = rbac_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    appr_service = WorkflowApprovalService(db_session)

    wf = wf_service.create_workflow(
        req_user.id,
        ws.id,
        WorkflowCreate(
            name="No Self Approval WF",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Gate",
                    config={"requester_can_approve": False, "approver_roles": ["admin", "member"]}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    exec_service.execute_workflow(req_user.id, ws.id, wf.id)
    approvals, _ = appr_service.list_approvals(ws.id, status="pending")
    approval = approvals[0]

    # Requester cannot self-approve
    with pytest.raises(PermissionError) as exc:
        appr_service.approve(approval.id, ws.id, req_user)
    assert "Self-approval is prohibited" in str(exc.value)

    # Admin can approve
    appr_service.approve(approval.id, ws.id, adm_user)
    db_session.refresh(approval)
    assert approval.status == WorkflowApprovalStatus.APPROVED

def test_unauthorized_role_rejection(db_session: Session, rbac_setup):
    req_user = rbac_setup["requester"]
    viewer_user = rbac_setup["viewer"]
    adm_user = rbac_setup["admin"]
    ws = rbac_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    appr_service = WorkflowApprovalService(db_session)

    wf = wf_service.create_workflow(
        req_user.id,
        ws.id,
        WorkflowCreate(
            name="Admin Only Gate",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="appr_1",
                    node_type=WorkflowNodeType.HUMAN_APPROVAL,
                    name="Gate",
                    config={"approver_roles": ["admin"]}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    exec_service.execute_workflow(req_user.id, ws.id, wf.id)
    approvals, _ = appr_service.list_approvals(ws.id, status="pending")
    approval = approvals[0]

    # Viewer role rejected
    with pytest.raises(PermissionError) as exc:
        appr_service.approve(approval.id, ws.id, viewer_user)
    assert "User role is not authorized" in str(exc.value)
