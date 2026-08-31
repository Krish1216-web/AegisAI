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
    WorkflowExecution,
    WorkflowExecutionStatus
)
from app.services.workflow_analytics import WorkflowAnalyticsService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def health_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Health Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Health")
    user = User(id=uuid.uuid4(), email="health@test.com", username="health_u", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_deterministic_health_classification(db_session: Session, health_setup):
    user = health_setup["user"]
    ws = health_setup["ws"]
    analytics_service = WorkflowAnalyticsService(db_session)

    # 1. Unexecuted Workflow -> HEALTHY
    wf_1 = Workflow(id=uuid.uuid4(), user_id=user.id, workspace_id=ws.id, name="Fresh WF")
    db_session.add(wf_1)

    # 2. Perfect Workflow (10 runs, 10 completed) -> HEALTHY
    wf_2 = Workflow(id=uuid.uuid4(), user_id=user.id, workspace_id=ws.id, name="Perfect WF")
    db_session.add(wf_2)
    for _ in range(5):
        e = WorkflowExecution(
            id=uuid.uuid4(),
            workflow_id=wf_2.id,
            user_id=user.id,
            workspace_id=ws.id,
            status=WorkflowExecutionStatus.COMPLETED,
            started_at=datetime.datetime.now(datetime.timezone.utc),
            completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(e)

    # 3. Flaky Workflow (2 completed, 2 failed, latest failed) -> WARNING
    wf_3 = Workflow(id=uuid.uuid4(), user_id=user.id, workspace_id=ws.id, name="Flaky WF")
    db_session.add(wf_3)
    for _ in range(2):
        e = WorkflowExecution(
            id=uuid.uuid4(),
            workflow_id=wf_3.id,
            user_id=user.id,
            workspace_id=ws.id,
            status=WorkflowExecutionStatus.COMPLETED,
            started_at=datetime.datetime.now(datetime.timezone.utc),
            completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(e)
    for _ in range(2):
        e = WorkflowExecution(
            id=uuid.uuid4(),
            workflow_id=wf_3.id,
            user_id=user.id,
            workspace_id=ws.id,
            status=WorkflowExecutionStatus.FAILED,
            started_at=datetime.datetime.now(datetime.timezone.utc),
            completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(e)

    # 4. Broken Workflow (1 completed, 9 failed) -> CRITICAL
    wf_4 = Workflow(id=uuid.uuid4(), user_id=user.id, workspace_id=ws.id, name="Broken WF")
    db_session.add(wf_4)
    e_c = WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id=wf_4.id,
        user_id=user.id,
        workspace_id=ws.id,
        status=WorkflowExecutionStatus.COMPLETED,
        started_at=datetime.datetime.now(datetime.timezone.utc),
        completed_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(e_c)
    for _ in range(9):
        e_f = WorkflowExecution(
            id=uuid.uuid4(),
            workflow_id=wf_4.id,
            user_id=user.id,
            workspace_id=ws.id,
            status=WorkflowExecutionStatus.FAILED,
            started_at=datetime.datetime.now(datetime.timezone.utc),
            completed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(e_f)

    db_session.commit()

    perf = analytics_service.get_workflow_performance(ws.id)
    items_by_name = {item["workflow_name"]: item for item in perf["items"]}

    assert items_by_name["Fresh WF"]["health"] == "HEALTHY"
    assert items_by_name["Perfect WF"]["health"] == "HEALTHY"
    assert items_by_name["Flaky WF"]["health"] == "WARNING"
    assert items_by_name["Broken WF"]["health"] == "CRITICAL"
