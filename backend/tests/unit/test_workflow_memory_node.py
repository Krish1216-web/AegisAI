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
def mem_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Mem Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Mem")
    user = User(id=uuid.uuid4(), email="mem_user@test.com", username="mem1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_memory_node_execution_and_context_recall(db_session: Session, mem_setup):
    u = mem_setup["user"]
    ws = mem_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Workflow: START -> MEMORY -> END
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Memory Recall Pipeline",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="mem_1",
                    node_type=WorkflowNodeType.MEMORY,
                    name="Context Memory",
                    config={
                        "query": "{{input.user_query}}",
                        "category": "SEMANTIC"
                    }
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Memory Processed"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="mem_1"),
                WorkflowEdgeCreate(source_node_key="mem_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        input_data={"user_query": "Project architecture notes"}
    )

    assert execution.status == WorkflowExecutionStatus.COMPLETED
    nodes_by_key = {en.node_key: en for en in execution.execution_nodes}
    assert nodes_by_key["mem_1"].status == WorkflowNodeStatus.COMPLETED
