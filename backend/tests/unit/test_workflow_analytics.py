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
    WorkflowExecution,
    WorkflowExecutionNode
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate
)
from app.services.workflow import WorkflowService
from app.services.workflow_execution import WorkflowExecutionService
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
def analytics_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Analytics Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Analytics")
    user = User(id=uuid.uuid4(), email="analytics_user@test.com", username="analytics_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_overview_and_performance_analytics(db_session: Session, analytics_setup):
    user = analytics_setup["user"]
    ws = analytics_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    analytics_service = WorkflowAnalyticsService(db_session)

    # 1. Create Workflow A
    wf_a = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Data Pipeline Alpha",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="transform_1",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Formatter",
                    config={"mapping": {"x": 1}}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="transform_1"),
                WorkflowEdgeCreate(source_node_key="transform_1", target_node_key="end_1")
            ]
        )
    )

    # Execute successfully twice
    e1 = exec_service.execute_workflow(user.id, ws.id, wf_a.id)
    e2 = exec_service.execute_workflow(user.id, ws.id, wf_a.id)

    # 2. Get overview metrics
    overview = analytics_service.get_overview_metrics(ws.id, days=7)
    assert overview["total_workflows"] == 1
    assert overview["total_executions"] == 2
    assert overview["completed_executions"] == 2
    assert overview["failed_executions"] == 0
    assert overview["success_rate"] == 100.0
    assert len(overview["time_series"]) == 7

    # 3. Get workflow performance
    perf = analytics_service.get_workflow_performance(ws.id, sort_by="total_runs")
    assert perf["total"] == 1
    item = perf["items"][0]
    assert item["workflow_name"] == "Data Pipeline Alpha"
    assert item["total_runs"] == 2
    assert item["success_rate"] == 100.0
    assert item["health"] == "HEALTHY"

def test_node_performance_and_failure_analytics(db_session: Session, analytics_setup):
    user = analytics_setup["user"]
    ws = analytics_setup["ws"]

    analytics_service = WorkflowAnalyticsService(db_session)

    # Create dummy execution with failed node containing secret
    exec_id = uuid.uuid4()
    wf_id = uuid.uuid4()
    wf = Workflow(id=wf_id, user_id=user.id, workspace_id=ws.id, name="Error Test WF")
    db_session.add(wf)
    db_session.flush()

    execution = WorkflowExecution(
        id=exec_id,
        workflow_id=wf_id,
        workflow_version=1,
        user_id=user.id,
        workspace_id=ws.id,
        status=WorkflowExecutionStatus.FAILED,
        started_at=datetime.datetime.now(datetime.timezone.utc),
        completed_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(execution)
    db_session.flush()

    failed_node = WorkflowExecutionNode(
        id=uuid.uuid4(),
        execution_id=exec_id,
        node_key="agent_step_1",
        status=WorkflowNodeStatus.FAILED,
        error="Connection failed with api_key=sk-1234567890abcdef and password=SuperSecretPassword123!",
        started_at=datetime.datetime.now(datetime.timezone.utc),
        completed_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(failed_node)
    db_session.commit()

    # Query node performance
    node_perf = analytics_service.get_node_performance(ws.id)
    assert node_perf["total"] == 1
    n_item = node_perf["items"][0]
    assert n_item["node_key"] == "agent_step_1"
    assert n_item["failed_count"] == 1
    assert n_item["failure_rate"] == 100.0
    assert n_item["bottleneck_category"] == "HIGH_FAILURE"

    # Query failure analytics & verify secret redaction
    failure_data = analytics_service.get_failure_analytics(ws.id)
    assert failure_data["total"] == 1
    f_item = failure_data["items"][0]
    assert "SuperSecretPassword123" not in f_item["error_summary"]
    assert "[REDACTED" in f_item["error_summary"] or "***" in f_item["error_summary"]
