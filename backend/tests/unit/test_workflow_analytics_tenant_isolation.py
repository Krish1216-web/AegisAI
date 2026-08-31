import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    WorkflowNodeType,
    WorkflowExecutionStatus
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
def tenant_analytics_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Analytics Tenant Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Analytics Alpha")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Analytics Beta")
    user_a = User(id=uuid.uuid4(), email="ua@test.com", username="ua", password_hash="pw", role_id=admin_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="ub@test.com", username="ub", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws_a, ws_b, user_a, user_b])
    db_session.flush()

    mem_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="admin")
    mem_b = WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role="admin")
    db_session.add_all([mem_a, mem_b])
    db_session.commit()

    return {"user_a": user_a, "user_b": user_b, "ws_a": ws_a, "ws_b": ws_b}

def test_cross_tenant_analytics_isolation(db_session: Session, tenant_analytics_setup):
    user_a = tenant_analytics_setup["user_a"]
    user_b = tenant_analytics_setup["user_b"]
    ws_a = tenant_analytics_setup["ws_a"]
    ws_b = tenant_analytics_setup["ws_b"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    analytics_service = WorkflowAnalyticsService(db_session)

    # Create & run workflow in Workspace A
    wf_a = wf_service.create_workflow(
        user_a.id,
        ws_a.id,
        WorkflowCreate(
            name="Confidential Pipeline A",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="end_1")
            ]
        )
    )
    exec_a = exec_service.execute_workflow(user_a.id, ws_a.id, wf_a.id)
    assert exec_a.status == WorkflowExecutionStatus.COMPLETED

    # Query metrics from Workspace B
    ov_b = analytics_service.get_overview_metrics(ws_b.id)
    assert ov_b["total_workflows"] == 0
    assert ov_b["total_executions"] == 0

    perf_b = analytics_service.get_workflow_performance(ws_b.id)
    assert perf_b["total"] == 0
    assert len(perf_b["items"]) == 0

    detail_b = analytics_service.get_execution_detail_analytics(ws_b.id, exec_a.id)
    assert detail_b is None
