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
def tenant_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Tenant Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS B")
    user_a = User(id=uuid.uuid4(), email="user_a@test.com", username="user_a", password_hash="pw", role_id=admin_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="user_b@test.com", username="user_b", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws_a, ws_b, user_a, user_b])
    db_session.flush()

    mem_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="admin")
    mem_b = WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role="admin")
    db_session.add_all([mem_a, mem_b])
    db_session.commit()

    return {"user_a": user_a, "user_b": user_b, "ws_a": ws_a, "ws_b": ws_b}

def test_cross_tenant_approval_isolation(db_session: Session, tenant_setup):
    user_a = tenant_setup["user_a"]
    user_b = tenant_setup["user_b"]
    ws_a = tenant_setup["ws_a"]
    ws_b = tenant_setup["ws_b"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    appr_service = WorkflowApprovalService(db_session)

    wf_a = wf_service.create_workflow(
        user_a.id,
        ws_a.id,
        WorkflowCreate(
            name="Tenant A Secret Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="appr_1", node_type=WorkflowNodeType.HUMAN_APPROVAL, name="Gate"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="appr_1"),
                WorkflowEdgeCreate(source_node_key="appr_1", target_node_key="end_1")
            ]
        )
    )

    exec_service.execute_workflow(user_a.id, ws_a.id, wf_a.id)
    approvals_a, _ = appr_service.list_approvals(ws_a.id, status="pending")
    app_a = approvals_a[0]

    # User B from Workspace B cannot list or get Workspace A's approvals
    approvals_b, count_b = appr_service.list_approvals(ws_b.id, status="pending")
    assert count_b == 0
    assert appr_service.get_approval(app_a.id, ws_b.id) is None

    # User B cannot approve Workspace A's request
    with pytest.raises(ValueError) as exc:
        appr_service.approve(app_a.id, ws_b.id, user_b)
    assert "not found" in str(exc.value)
