import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import WorkflowNodeType
from app.schemas.workflow import WorkflowCreate, WorkflowNodeCreate, WorkflowEdgeCreate, WorkflowExecutionCreate
from app.api.v1.endpoints.workflows import (
    create_workflow,
    list_workflows,
    get_workflow,
    validate_workflow,
    activate_workflow,
    execute_workflow
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def api_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="API Workflow Org")
    role = Role(id=uuid.uuid4(), name="User")
    db_session.add_all([org, role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS API")
    user = User(id=uuid.uuid4(), email="api_wf_user@test.com", username="api_wf", password_hash="pw", role_id=role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

@pytest.mark.asyncio
async def test_workflow_api_endpoints_flow(db_session: Session, api_setup):
    u = api_setup["user"]

    # 1. POST /workflows
    payload = WorkflowCreate(
        name="API Test Workflow",
        description="Testing endpoint flow",
        nodes=[
            WorkflowNodeCreate(node_key="s1", node_type=WorkflowNodeType.START, name="Start", config={}),
            WorkflowNodeCreate(node_key="t1", node_type=WorkflowNodeType.TRANSFORM, name="Transform", config={"mapping": {"out": "{{input.msg}}"}}),
            WorkflowNodeCreate(node_key="e1", node_type=WorkflowNodeType.END, name="End", config={})
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="s1", target_node_key="t1"),
            WorkflowEdgeCreate(source_node_key="t1", target_node_key="e1")
        ]
    )
    created = await create_workflow(payload=payload, current_user=u, db=db_session)
    assert created.name == "API Test Workflow"
    assert created.version == 1

    # 2. GET /workflows
    wf_list = await list_workflows(limit=10, offset=0, status=None, current_user=u, db=db_session)
    assert wf_list.total == 1
    assert len(wf_list.workflows) == 1

    # 3. POST /workflows/{id}/validate
    val_res = await validate_workflow(workflow_id=created.id, current_user=u, db=db_session)
    assert val_res.valid is True

    # 4. POST /workflows/{id}/activate
    activated = await activate_workflow(workflow_id=created.id, current_user=u, db=db_session)
    assert activated.is_active is True

    # 5. POST /workflows/{id}/execute
    exec_payload = WorkflowExecutionCreate(input_data={"msg": "Hello API"})
    exec_res = await execute_workflow(workflow_id=created.id, payload=exec_payload, current_user=u, db=db_session)
    assert exec_res.status == "completed"
    assert len(exec_res.execution_nodes) == 3
