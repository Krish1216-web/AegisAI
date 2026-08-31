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
    WorkflowStatus
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowVariableCreate,
    WorkflowDefinitionUpdate
)
from app.services.workflow import WorkflowService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def config_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Config Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Config")
    user = User(id=uuid.uuid4(), email="cfg_user@test.com", username="cfg1", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    svc = WorkflowService(db_session)
    wf = svc.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Multi-Node Graph",
            nodes=[
                WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1")]
        )
    )

    return {"user": user, "ws": ws, "wf": wf}

def test_multi_node_type_configuration_and_persistence(db_session: Session, config_setup):
    svc = WorkflowService(db_session)
    u = config_setup["user"]
    ws = config_setup["ws"]
    wf = config_setup["wf"]

    # Graph composing: START -> AGENT -> RAG -> GRAPH -> MEMORY -> MCP_TOOL -> TRANSFORM -> END
    payload = WorkflowDefinitionUpdate(
        expected_version=1,
        name="Enterprise Workflow",
        nodes=[
            WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start Trigger", config={"description": "Lead input"}),
            WorkflowNodeCreate(node_key="agent_1", node_type=WorkflowNodeType.AGENT, name="Triage Agent", config={"goal": "Classify incoming inquiry", "agent_type": "ANALYSIS"}),
            WorkflowNodeCreate(node_key="rag_1", node_type=WorkflowNodeType.RAG, name="Knowledge Search", config={"query": "{{nodes.agent_1.output.topic}}", "top_k": 3, "similarity_threshold": 0.75}),
            WorkflowNodeCreate(node_key="graph_1", node_type=WorkflowNodeType.GRAPH, name="Entity Reasoning", config={"query": "{{input.company}}", "max_depth": 2}),
            WorkflowNodeCreate(node_key="memory_1", node_type=WorkflowNodeType.MEMORY, name="Recall Context", config={"query": "{{input.user_id}}", "category": "SEMANTIC"}),
            WorkflowNodeCreate(node_key="mcp_tool_1", node_type=WorkflowNodeType.MCP_TOOL, name="Enrichment Tool", config={"tool_name": "clearbit_lookup", "server_name": "Clearbit MCP"}),
            WorkflowNodeCreate(node_key="transform_1", node_type=WorkflowNodeType.TRANSFORM, name="Consolidator", config={"mapping": {"summary": "{{nodes.agent_1.output.result}}"}}),
            WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="Final Result", config={"output_template": "Summary: {{nodes.transform_1.output.summary}}"})
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="start_1", target_node_key="agent_1"),
            WorkflowEdgeCreate(source_node_key="agent_1", target_node_key="rag_1"),
            WorkflowEdgeCreate(source_node_key="rag_1", target_node_key="graph_1"),
            WorkflowEdgeCreate(source_node_key="graph_1", target_node_key="memory_1"),
            WorkflowEdgeCreate(source_node_key="memory_1", target_node_key="mcp_tool_1"),
            WorkflowEdgeCreate(source_node_key="mcp_tool_1", target_node_key="transform_1"),
            WorkflowEdgeCreate(source_node_key="transform_1", target_node_key="end_1")
        ]
    )

    updated = svc.update_workflow_definition(u.id, ws.id, wf.id, payload)
    assert updated.version == 2
    assert len(updated.nodes) == 8
    assert len(updated.edges) == 7

    node_types = {n.node_key: n.node_type for n in updated.nodes}
    assert node_types["mcp_tool_1"] == WorkflowNodeType.MCP_TOOL
    assert node_types["graph_1"] == WorkflowNodeType.GRAPH

def test_workflow_clone_feature(db_session: Session, config_setup):
    svc = WorkflowService(db_session)
    u = config_setup["user"]
    ws = config_setup["ws"]
    wf = config_setup["wf"]

    cloned = svc.clone_workflow(u.id, ws.id, wf.id, clone_name="Cloned Copy")
    assert cloned is not None
    assert cloned.id != wf.id
    assert cloned.name == "Cloned Copy"
    assert cloned.version == 1
    assert cloned.status == WorkflowStatus.DRAFT
    assert len(cloned.nodes) == len(wf.nodes)
    assert len(cloned.edges) == len(wf.edges)
