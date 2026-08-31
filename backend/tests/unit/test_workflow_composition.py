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

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def composition_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Comp Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Comp")
    user = User(id=uuid.uuid4(), email="comp_user@test.com", username="comp_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_sub_workflow_invocation_and_data_flow(db_session: Session, composition_setup):
    user = composition_setup["user"]
    ws = composition_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # 1. Create Child Workflow: Formats a name string
    child_wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Child String Formatter",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="transform_1",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Formatter",
                    config={"mapping": {"formatted_name": "Dear {{input.raw_name}}"}}
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Child processed: {{nodes.transform_1.output.transformed.formatted_name}}"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="transform_1"),
                WorkflowEdgeCreate(source_node_key="transform_1", target_node_key="end_1")
            ]
        )
    )

    # 2. Create Parent Workflow: Calls child sub-workflow
    parent_wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Parent Orchestrator",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="sub_1",
                    node_type=WorkflowNodeType.SUB_WORKFLOW,
                    name="Invoke Child",
                    config={
                        "workflow_id": str(child_wf.id),
                        "input_mapping": {"raw_name": "{{input.user_name}}"}
                    }
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Parent received: {{nodes.sub_1.output.result}}"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="sub_1"),
                WorkflowEdgeCreate(source_node_key="sub_1", target_node_key="end_1")
            ]
        )
    )

    # 3. Execute parent workflow
    parent_exec = exec_service.execute_workflow(
        user.id,
        ws.id,
        parent_wf.id,
        input_data={"user_name": "Alice"}
    )

    assert parent_exec.status == WorkflowExecutionStatus.COMPLETED
    assert "Child processed: Dear Alice" in str(parent_exec.output_data)

def test_sub_workflow_recursion_and_self_invocation_detection(db_session: Session, composition_setup):
    user = composition_setup["user"]
    ws = composition_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Create a workflow that attempts to invoke itself as a sub-workflow
    rec_wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Recursive Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="sub_self",
                    node_type=WorkflowNodeType.SUB_WORKFLOW,
                    name="Self Sub",
                    config={"workflow_name": "Recursive Workflow"}
                ),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="sub_self"),
                WorkflowEdgeCreate(source_node_key="sub_self", target_node_key="end_1")
            ]
        )
    )

    # Executing must detect recursion and fail safely
    exec_record = exec_service.execute_workflow(user.id, ws.id, rec_wf.id)
    assert exec_record.status == WorkflowExecutionStatus.FAILED
    assert "recursion/cycle detected" in str(exec_record.error)
