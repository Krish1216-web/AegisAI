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
    WorkflowUpdate,
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
def multi_tenant_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Multi Tenant WF Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    # Tenant 1
    ws1 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS 1")
    u1 = User(id=uuid.uuid4(), email="u1_wf@test.com", username="u1_wf", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws1, u1])
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=ws1.id, user_id=u1.id, role="member"))

    # Tenant 2
    ws2 = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS 2")
    u2 = User(id=uuid.uuid4(), email="u2_wf@test.com", username="u2_wf", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws2, u2])
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=ws2.id, user_id=u2.id, role="member"))
    db_session.commit()

    wf_svc = WorkflowService(db_session)
    wf1 = wf_svc.create_workflow(
        u1.id,
        ws1.id,
        WorkflowCreate(
            name="Workflow WS 1",
            nodes=[
                WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", config={}),
                WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", config={})
            ],
            edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
        )
    )

    return {"u1": u1, "ws1": ws1, "wf1": wf1, "u2": u2, "ws2": ws2}

def test_cross_tenant_workflow_retrieval_and_listing(db_session: Session, multi_tenant_setup):
    s = multi_tenant_setup
    svc = WorkflowService(db_session)

    # User 1 queries WS 1 -> finds wf1
    wf1 = svc.get_workflow(s["u1"].id, s["ws1"].id, s["wf1"].id)
    assert wf1 is not None

    # User 2 in WS 2 attempts to query wf1 -> None (isolated)
    cross_wf = svc.get_workflow(s["u2"].id, s["ws2"].id, s["wf1"].id)
    assert cross_wf is None

    # Listing workflows in WS 2 returns 0
    wfs2, total2 = svc.list_workflows(s["u2"].id, s["ws2"].id)
    assert total2 == 0

def test_cross_tenant_workflow_update_and_delete_denial(db_session: Session, multi_tenant_setup):
    s = multi_tenant_setup
    svc = WorkflowService(db_session)

    # User 2 attempts to update wf1 -> None
    update_res = svc.update_workflow(s["u2"].id, s["ws2"].id, s["wf1"].id, WorkflowUpdate(name="Hijacked Name"))
    assert update_res is None

    # User 2 attempts to delete wf1 -> False
    delete_res = svc.delete_workflow(s["u2"].id, s["ws2"].id, s["wf1"].id)
    assert delete_res is False

def test_cross_tenant_workflow_execution_denial(db_session: Session, multi_tenant_setup):
    s = multi_tenant_setup
    exec_svc = WorkflowExecutionService(db_session)

    # User 2 attempts to execute wf1 in WS 2 context -> raises ValueError
    with pytest.raises(ValueError, match="not found in active workspace"):
        exec_svc.execute_workflow(s["u2"].id, s["ws2"].id, s["wf1"].id, {})
