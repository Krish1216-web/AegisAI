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
    WorkflowScheduleStatus,
    WorkflowScheduleType,
    WorkflowScheduleConcurrencyPolicy,
    WorkflowExecutionStatus
)
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
def sched_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Sched Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sched")
    user = User(id=uuid.uuid4(), email="sched_user@test.com", username="sched_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_cron_schedule_lifecycle_and_execution_provenance(db_session: Session, sched_setup):
    user = sched_setup["user"]
    ws = sched_setup["ws"]

    wf_service = WorkflowService(db_session)
    sched_service = WorkflowSchedulerService(db_session)

    # 1. Create Workflow
    wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Scheduled Data Ingestion",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="transform_1",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Formatter",
                    config={"mapping": {"source": "{{input._schedule_provenance.schedule_name}}"}}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="transform_1"),
                WorkflowEdgeCreate(source_node_key="transform_1", target_node_key="end_1")
            ]
        )
    )

    # 2. Create Schedule pinned to workflow version 1
    schedule = sched_service.create_schedule(
        user.id,
        ws.id,
        WorkflowScheduleCreate(
            workflow_id=wf.id,
            name="Daily Morning Sync",
            schedule_type="cron",
            cron_expression="0 9 * * *",
            timezone="UTC",
            is_enabled=True,
            concurrency_policy="skip"
        )
    )

    assert schedule.status == WorkflowScheduleStatus.ACTIVE
    assert schedule.workflow_version == 1
    assert schedule.next_run_at is not None

    # 3. Pause & Resume
    paused = sched_service.pause_schedule(user.id, ws.id, schedule.id)
    assert paused.status == WorkflowScheduleStatus.PAUSED
    assert paused.next_run_at is None

    resumed = sched_service.resume_schedule(user.id, ws.id, schedule.id)
    assert resumed.status == WorkflowScheduleStatus.ACTIVE
    assert resumed.next_run_at is not None

    # 4. Manual Trigger
    execution = sched_service.trigger_schedule(user.id, ws.id, schedule.id, is_manual=True)
    assert execution.status == WorkflowExecutionStatus.COMPLETED
    assert execution.input_data["_schedule_provenance"]["schedule_name"] == "Daily Morning Sync"

    db_session.refresh(schedule)
    assert schedule.total_runs == 1
    assert schedule.last_execution_id == execution.id

def test_one_time_schedule_completes_after_run(db_session: Session, sched_setup):
    user = sched_setup["user"]
    ws = sched_setup["ws"]

    wf_service = WorkflowService(db_session)
    sched_service = WorkflowSchedulerService(db_session)

    wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="One Time WF",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="end_1")
            ]
        )
    )

    future_run = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
    schedule = sched_service.create_schedule(
        user.id,
        ws.id,
        WorkflowScheduleCreate(
            workflow_id=wf.id,
            name="Run Later Today",
            schedule_type="one_time",
            run_at=future_run,
            timezone="UTC"
        )
    )
    assert schedule.schedule_type == WorkflowScheduleType.ONE_TIME
    assert schedule.status == WorkflowScheduleStatus.ACTIVE

    # Trigger
    execution = sched_service.trigger_schedule(user.id, ws.id, schedule.id, is_manual=False)
    assert execution.status == WorkflowExecutionStatus.COMPLETED

    db_session.refresh(schedule)
    assert schedule.status == WorkflowScheduleStatus.COMPLETED
    assert schedule.is_enabled is False
    assert schedule.next_run_at is None
