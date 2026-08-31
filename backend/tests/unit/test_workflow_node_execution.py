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
    WorkflowEdgeCreate,
    WorkflowVariableCreate
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
def exec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Exec Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Exec")
    user = User(id=uuid.uuid4(), email="exec_user@test.com", username="exec1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_start_end_transform_execution(db_session: Session, exec_setup):
    u = exec_setup["user"]
    ws = exec_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Workflow: START -> TRANSFORM -> END
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Data Pipeline",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="transform_1",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Formatter",
                    config={
                        "mapping": {
                            "greeting": "Hello {{input.user_name}}",
                            "status": "active"
                        }
                    }
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={
                        "output_template": "Welcome: {{nodes.transform_1.output.greeting}}"
                    }
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="transform_1"),
                WorkflowEdgeCreate(source_node_key="transform_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        input_data={"user_name": "Alice"}
    )

    assert execution.status == WorkflowExecutionStatus.COMPLETED
    assert execution.output_data == "Welcome: Hello Alice"
    assert len(execution.execution_nodes) == 3
    for en in execution.execution_nodes:
        assert en.status == WorkflowNodeStatus.COMPLETED

def test_conditional_routing_and_branch_skipping(db_session: Session, exec_setup):
    u = exec_setup["user"]
    ws = exec_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Graph with CONDITION:
    # START -> CONDITION -> (True branch: TRANSFORM_A -> END)
    #                   \-> (False branch: TRANSFORM_B -> END)
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Conditional Decision",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="cond_1",
                    node_type=WorkflowNodeType.CONDITION,
                    name="Age Check",
                    config={
                        "left": "{{input.age}}",
                        "operator": "greater_or_equal",
                        "right": 18
                    }
                ),
                WorkflowNodeCreate(
                    node_key="transform_adult",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Adult Handler",
                    config={"mapping": {"category": "adult"}}
                ),
                WorkflowNodeCreate(
                    node_key="transform_minor",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Minor Handler",
                    config={"mapping": {"category": "minor"}}
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Processed category"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="cond_1"),
                WorkflowEdgeCreate(
                    source_node_key="cond_1",
                    target_node_key="transform_adult",
                    condition={"left": "{{nodes.cond_1.output.result}}", "operator": "equals", "right": True}
                ),
                WorkflowEdgeCreate(
                    source_node_key="cond_1",
                    target_node_key="transform_minor",
                    condition={"left": "{{nodes.cond_1.output.result}}", "operator": "equals", "right": False}
                ),
                WorkflowEdgeCreate(source_node_key="transform_adult", target_node_key="end_1"),
                WorkflowEdgeCreate(source_node_key="transform_minor", target_node_key="end_1")
            ]
        )
    )

    # Test age = 21 -> Adult branch taken, minor branch skipped
    exec_adult = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        input_data={"age": 21}
    )
    assert exec_adult.status == WorkflowExecutionStatus.COMPLETED
    nodes_by_key = {en.node_key: en.status for en in exec_adult.execution_nodes}
    assert nodes_by_key["transform_adult"] == WorkflowNodeStatus.COMPLETED
    assert nodes_by_key["transform_minor"] == WorkflowNodeStatus.SKIPPED
