import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import WorkflowNodeType
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowScheduleCreate
)
from app.services.workflow import WorkflowService
from app.services.workflow_scheduler import WorkflowSchedulerService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def tenant_sched_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Tenant Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Alpha")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Beta")
    user_a = User(id=uuid.uuid4(), email="user_a@test.com", username="user_a", password_hash="pw", role_id=admin_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="user_b@test.com", username="user_b", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws_a, ws_b, user_a, user_b])
    db_session.flush()

    mem_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="admin")
    mem_b = WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role="admin")
    db_session.add_all([mem_a, mem_b])
    db_session.commit()

    return {"user_a": user_a, "user_b": user_b, "ws_a": ws_a, "ws_b": ws_b}

def test_cross_tenant_schedule_isolation(db_session: Session, tenant_sched_setup):
    user_a = tenant_sched_setup["user_a"]
    user_b = tenant_sched_setup["user_b"]
    ws_a = tenant_sched_setup["ws_a"]
    ws_b = tenant_sched_setup["ws_b"]

    wf_service = WorkflowService(db_session)
    sched_service = WorkflowSchedulerService(db_session)

    wf_a = wf_service.create_workflow(
        user_a.id,
        ws_a.id,
        WorkflowCreate(
            name="Workspace A Secret Flow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="end_1")
            ]
        )
    )

    sched_a = sched_service.create_schedule(
        user_a.id,
        ws_a.id,
        WorkflowScheduleCreate(
            workflow_id=wf_a.id,
            name="Alpha Daily Sync",
            schedule_type="cron",
            cron_expression="0 9 * * *"
        )
    )

    # User B / Workspace B cannot access or list Workspace A's schedules
    schedules_b, total_b = sched_service.list_schedules(ws_b.id)
    assert total_b == 0
    assert sched_service.get_schedule(sched_a.id, ws_b.id) is None

    # User B cannot trigger or delete Workspace A's schedule
    with pytest.raises(ValueError) as exc:
        sched_service.trigger_schedule(user_b.id, ws_b.id, sched_a.id, is_manual=True)
    assert "not found" in str(exc.value)

    assert sched_service.delete_schedule(user_b.id, ws_b.id, sched_a.id) is False
