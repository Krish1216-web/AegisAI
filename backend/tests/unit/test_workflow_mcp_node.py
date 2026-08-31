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
def mcp_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="MCP Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS MCP")
    user = User(id=uuid.uuid4(), email="mcp_user@test.com", username="mcp1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_mcp_tool_resource_and_prompt_execution(db_session: Session, mcp_setup):
    u = mcp_setup["user"]
    ws = mcp_setup["ws"]
    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    # Workflow: START -> MCP_TOOL -> MCP_RESOURCE -> MCP_PROMPT -> END
    wf = wf_service.create_workflow(
        u.id,
        ws.id,
        WorkflowCreate(
            name="MCP Hybrid Workflow",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(
                    node_key="mcp_tool_1",
                    node_type=WorkflowNodeType.MCP_TOOL,
                    name="MCP Enrichment",
                    config={
                        "tool_name": "company_lookup",
                        "server_name": "Clearbit MCP",
                        "arguments": {"domain": "{{input.domain}}"}
                    }
                ),
                WorkflowNodeCreate(
                    node_key="mcp_res_1",
                    node_type=WorkflowNodeType.MCP_RESOURCE,
                    name="MCP Resource Read",
                    config={"uri": "mcp://github/repo/docs"}
                ),
                WorkflowNodeCreate(
                    node_key="mcp_prompt_1",
                    node_type=WorkflowNodeType.MCP_PROMPT,
                    name="MCP Prompt Template",
                    config={
                        "prompt_name": "summarize_spec",
                        "arguments": {"content": "{{nodes.mcp_res_1.output.content}}"}
                    }
                ),
                WorkflowNodeCreate(
                    node_key="end_1",
                    node_type=WorkflowNodeType.END,
                    name="End",
                    config={"output_template": "MCP Execution Finished"}
                )
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="mcp_tool_1"),
                WorkflowEdgeCreate(source_node_key="mcp_tool_1", target_node_key="mcp_res_1"),
                WorkflowEdgeCreate(source_node_key="mcp_res_1", target_node_key="mcp_prompt_1"),
                WorkflowEdgeCreate(source_node_key="mcp_prompt_1", target_node_key="end_1")
            ]
        )
    )

    execution = exec_service.execute_workflow(
        user_id=u.id,
        workspace_id=ws.id,
        workflow_id=wf.id,
        input_data={"domain": "example.com"}
    )

    assert execution.status == WorkflowExecutionStatus.COMPLETED
    nodes_by_key = {en.node_key: en for en in execution.execution_nodes}
    assert nodes_by_key["mcp_tool_1"].status == WorkflowNodeStatus.COMPLETED
    assert nodes_by_key["mcp_res_1"].status == WorkflowNodeStatus.COMPLETED
    assert nodes_by_key["mcp_prompt_1"].status == WorkflowNodeStatus.COMPLETED
    # Untrusted MCP provenance
    assert nodes_by_key["mcp_res_1"].output_data.get("untrusted") is True
    assert nodes_by_key["mcp_prompt_1"].output_data.get("untrusted") is True
