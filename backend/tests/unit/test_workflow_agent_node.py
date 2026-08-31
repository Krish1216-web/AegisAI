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
def agent_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Agent Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Agent")
    user = User(id=uuid.uuid4(), email="agent_user@test.com", username="agent1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_agent_node_execution_and_context_propagation(db_session: Session, agent_setup):
    u = agent_setup["user"]
    ws = agent_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Workflow: START -> AGENT -> TRANSFORM -> END
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="Agent Task Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="agent_1",
                    node_type=WorkflowNodeType.AGENT,
                    name="Summarizer",
                    config={
                        "agent_type": "ANALYSIS",
                        "goal": "Analyze query: {{input.topic}}"
                    }
                ),
                WorkflowNodeCreate(
                    node_key="transform_1",
                    node_type=WorkflowNodeType.TRANSFORM,
                    name="Formatter",
                    config={
                        "mapping": {
                            "summary": "{{nodes.agent_1.output.result}}"
                        }
                    }
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "Report: {{nodes.transform_1.output.summary}}"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="agent_1"),
                WorkflowEdgeCreate(source_node_key="agent_1", target_node_key="transform_1"),
                WorkflowEdgeCreate(source_node_key="transform_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        input_data={"topic": "Quantum Computing"}
    )

    assert execution.status == WorkflowExecutionStatus.COMPLETED
    assert "Quantum Computing" in str(execution.output_data)
    nodes_by_key = {en.node_key: en for en in execution.execution_nodes}
    assert nodes_by_key["agent_1"].status == WorkflowNodeStatus.COMPLETED
