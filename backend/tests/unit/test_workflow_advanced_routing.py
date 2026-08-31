import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowNodeType,
    WorkflowExecutionStatus,
    WorkflowNodeStatus
)
from app.schemas.workflow import (
    WorkflowCreate,
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
def routing_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Route Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Route")
    user = User(id=uuid.uuid4(), email="route_user@test.com", username="route1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_multi_branch_priority_and_default_fallback(db_session: Session, routing_setup):
    u = routing_setup["user"]
    ws = routing_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Workflow: START -> CONDITION ->
    #   (Branch 1: score >= 80 -> TRANSFORM_HIGH -> END) [priority 10]
    #   (Branch 2: score >= 50 -> TRANSFORM_MID  -> END) [priority 5]
    #   (Branch 3: default     -> TRANSFORM_LOW  -> END) [is_default: true]
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Multi Branch Tier Router",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="cond_1", node_type=WorkflowNodeType.CONDITION, name="Tier Router"),
                WorkflowNodeCreate(
                    node_key="trans_high",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="High Tier",
                    config={"mapping": {"tier": "HIGH"}}
                ),
                WorkflowNodeCreate(
                    node_key="trans_mid",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Mid Tier",
                    config={"mapping": {"tier": "MID"}}
                ),
                WorkflowNodeCreate(
                    node_key="trans_low",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Low Tier",
                    config={"mapping": {"tier": "LOW"}}
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Tier Assigned"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="cond_1"),
                WorkflowEdgeCreate(
                    source_node_key="cond_1",
                    target_node_key="trans_high",
                    priority=10,
                    condition={"left": "{{input.score}}", "operator": "greater_or_equal", "right": 80}
                ),
                WorkflowEdgeCreate(
                    source_node_key="cond_1",
                    target_node_key="trans_mid",
                    priority=5,
                    condition={
                        "logic": "AND",
                        "conditions": [
                            {"left": "{{input.score}}", "operator": "greater_or_equal", "right": 50},
                            {"left": "{{input.score}}", "operator": "less_than", "right": 80}
                        ]
                    }
                ),
                WorkflowEdgeCreate(
                    source_node_key="cond_1",
                    target_node_key="trans_low",
                    priority=1,
                    condition={"is_default": True}
                ),
                WorkflowEdgeCreate(source_node_key="trans_high", target_node_key="end_1"),
                WorkflowEdgeCreate(source_node_key="trans_mid", target_node_key="end_1"),
                WorkflowEdgeCreate(source_node_key="trans_low", target_node_key="end_1")
            ]
        )
    )

    # 1. Test score = 95 -> HIGH tier taken, MID/LOW skipped
    exec_high = exec_service.execute_workflow(u.id, ws.id, wf.id, input_data={"score": 95})
    assert exec_high.status == WorkflowExecutionStatus.COMPLETED
    nodes_high = {n.node_key: n.status for n in exec_high.execution_nodes}
    assert nodes_high["trans_high"] == WorkflowNodeStatus.COMPLETED
    assert nodes_high["trans_mid"] == WorkflowNodeStatus.SKIPPED
    assert nodes_high["trans_low"] == WorkflowNodeStatus.SKIPPED

    # 2. Test score = 65 -> MID tier taken, HIGH/LOW skipped
    exec_mid = exec_service.execute_workflow(u.id, ws.id, wf.id, input_data={"score": 65})
    assert exec_mid.status == WorkflowExecutionStatus.COMPLETED
    nodes_mid = {n.node_key: n.status for n in exec_mid.execution_nodes}
    assert nodes_mid["trans_high"] == WorkflowNodeStatus.SKIPPED
    assert nodes_mid["trans_mid"] == WorkflowNodeStatus.COMPLETED
    assert nodes_mid["trans_low"] == WorkflowNodeStatus.SKIPPED

    # 3. Test score = 30 -> Fallback to LOW tier, HIGH/MID skipped
    exec_low = exec_service.execute_workflow(u.id, ws.id, wf.id, input_data={"score": 30})
    assert exec_low.status == WorkflowExecutionStatus.COMPLETED
    nodes_low = {n.node_key: n.status for n in exec_low.execution_nodes}
    assert nodes_low["trans_high"] == WorkflowNodeStatus.SKIPPED
    assert nodes_low["trans_mid"] == WorkflowNodeStatus.SKIPPED
    assert nodes_low["trans_low"] == WorkflowNodeStatus.COMPLETED
