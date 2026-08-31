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
def e2e_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="E2E Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS E2E")
    user = User(id=uuid.uuid4(), email="e2e_user@test.com", username="e2e_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_full_complex_workflow_orchestration_e2e(db_session: Session, e2e_setup):
    """
    Complex End-to-End DAG test:
    1. Child workflow (data enricher)
    2. Parent workflow:
       START -> PARALLEL -> (BRANCH_A, BRANCH_B) -> MERGE -> SUB_WORKFLOW (Child) -> END
    3. Verify execution state, node progression, and analytics visibility.
    """
    user = e2e_setup["user"]
    ws = e2e_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)
    analytics_service = WorkflowAnalyticsService(db_session)

    # 1. Create Child Workflow
    child_wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="E2E Child Enricher",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="transform_child",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Enricher",
                    config={"mapping": {"status": "ENRICHED_BY_CHILD", "tag": "e2e-verified"}}
                ),
                WorkflowNodeCreate(
                    node_key="end_child",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Enrichment complete: {{nodes.transform_child.output.transformed.status}}"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="transform_child"),
                WorkflowEdgeCreate(source_node_key="transform_child", target_node_key="end_child")
            ]
        )
    )

    # 2. Create Complex Master Workflow
    master_wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="E2E Master Orchestrator",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="par_1",
                    node_type=WorkflowNodeType.PARALLEL,
                    name="Parallel Fan-Out",
                    config={"max_concurrency": 5}
                ),
                WorkflowNodeCreate(
                    node_key="branch_1",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Branch 1 Transform",
                    config={"mapping": {"part1": "Alpha"}}
                ),
                WorkflowNodeCreate(
                    node_key="branch_2",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Branch 2 Transform",
                    config={"mapping": {"part2": "Beta"}}
                ),
                WorkflowNodeCreate(
                    node_key="merge_1",
                    node_type=WorkflowNodeType.MERGE,
                    name="Merge In",
                    config={"policy": "all", "merge_key": "branches"}
                ),
                WorkflowNodeCreate(
                    node_key="sub_1",
                    node_type=WorkflowNodeType.SUB_WORKFLOW,
                    name="Call Enricher Child",
                    config={"workflow_id": str(child_wf.id)}
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "E2E Result: {{nodes.sub_1.output.result}}"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="par_1"),
                WorkflowEdgeCreate(source_node_key="par_1", target_node_key="branch_1"),
                WorkflowEdgeCreate(source_node_key="par_1", target_node_key="branch_2"),
                WorkflowEdgeCreate(source_node_key="branch_1", target_node_key="merge_1"),
                WorkflowEdgeCreate(source_node_key="branch_2", target_node_key="merge_1"),
                WorkflowEdgeCreate(source_node_key="merge_1", target_node_key="sub_1"),
                WorkflowEdgeCreate(source_node_key="sub_1", target_node_key="end_1")
            ]
        )
    )

    # 3. Execute Master Workflow
    master_exec = exec_service.execute_workflow(user.id, ws.id, master_wf.id, input_data={"client": "E2E Test"})
    assert master_exec.status == WorkflowExecutionStatus.COMPLETED
    assert "Enrichment complete: ENRICHED_BY_CHILD" in str(master_exec.output_data)

    # 4. Verify Analytics Observation
    overview = analytics_service.get_overview_metrics(ws.id, days=7)
    assert overview["total_executions"] == 2  # Parent + Child
    assert overview["completed_executions"] == 2
    assert overview["success_rate"] == 100.0

    comp = analytics_service.get_composition_analytics(ws.id)
    assert comp["total_sub_workflow_invocations"] >= 1
    assert comp["total_parallel_fanouts"] >= 1
    assert comp["total_merge_fanins"] >= 1
