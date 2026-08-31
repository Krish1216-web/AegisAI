import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowNodeType
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
def def_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Def Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Def")
    user = User(id=uuid.uuid4(), email="def_user@test.com", username="def1", password_hash="pw", role_id=role.id, is_active=True)
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
            name="Initial Graph",
            nodes=[
                WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", position={"x": 50, "y": 100}),
                WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", position={"x": 300, "y": 100})
            ],
            edges=[WorkflowEdgeCreate(source_node_key="s1", target_node_key="e1", priority=1)],
            variables=[WorkflowVariableCreate(name="env", value="prod", value_type="string")]
        )
    )

    return {"user": user, "ws": ws, "wf": wf}

def test_workflow_definition_retrieval_and_update(db_session: Session, def_setup):
    svc = WorkflowService(db_session)
    u = def_setup["user"]
    ws = def_setup["ws"]
    wf = def_setup["wf"]

    # 1. Get Definition
    fetched = svc.get_workflow_definition(u.id, ws.id, wf.id)
    assert fetched is not None
    assert fetched.version == 1
    assert len(fetched.nodes) == 2
    assert len(fetched.edges) == 1
    assert len(fetched.variables) == 1

    # 2. Update Definition: add agent node in between
    update_payload = WorkflowDefinitionUpdate(
        expected_version=1,
        name="Updated Visual Graph",
        description="Graph updated from visual builder",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", position={"x": 50, "y": 100}),
            WorkflowNodeCreate(node_key="agent_1", node_type=WorkflowNodeType.AGENT, name="Researcher", config={"goal": "Find docs"}, position={"x": 200, "y": 100}),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", position={"x": 400, "y": 100})
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="s1", target_node_key="agent_1", priority=1),
            WorkflowEdgeCreate(source_node_key="agent_1", target_node_key="e1", priority=1)
        ],
        variables=[
            WorkflowVariableCreate(name="env", value="staging", value_type="string"),
            WorkflowVariableCreate(name="secret_key", value="super_secret", value_type="string", is_secret=True)
        ]
    )

    updated = svc.update_workflow_definition(u.id, ws.id, wf.id, update_payload)
    assert updated.version == 2
    assert updated.name == "Updated Visual Graph"
    assert len(updated.nodes) == 3
    assert len(updated.edges) == 2
    assert len(updated.variables) == 2

    # Secret variable is encrypted
    sec_var = next(v for v in updated.variables if v.name == "secret_key")
    assert sec_var.is_secret is True
    assert sec_var.value != "super_secret"  # encoded/encrypted
