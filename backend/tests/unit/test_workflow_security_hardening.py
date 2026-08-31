import pytest
import uuid
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.workflow import (
    Workflow,
    WorkflowNodeType,
    WorkflowExecutionStatus,
    WorkflowExecution
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate
)
from app.services.workflow import WorkflowService
from app.services.workflow_execution import (
    WorkflowExecutionService,
    WorkflowExecutionContext
)
from app.services.workflow_validation import WorkflowValidationService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def sec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db_session.add_all([org, admin_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Sec")
    user = User(id=uuid.uuid4(), email="sec_user@test.com", username="sec_user", password_hash="pw", role_id=admin_role.id, is_active=True)
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws}

def test_expression_injection_defense():
    """Verify that expressions cannot execute Python code or system calls."""
    ctx = WorkflowExecutionContext(
        execution_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        workflow_version=1,
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        input_data={"safe_key": "safe_val"},
        variables={"var_1": "123"}
    )

    # 1. Malicious Python code injection attempts
    malicious_exprs = [
        "{{__import__('os').system('ls')}}",
        "{{eval('1+1')}}",
        "{{exec('import sys')}}",
        "{{open('/etc/passwd').read()}}",
        "{{input.__class__.__mro__}}"
    ]

    for expr in malicious_exprs:
        resolved = ctx.resolve_expression(expr)
        # Should not execute and return empty string or safe un-evaluated text
        assert resolved in ("", expr, None)

    # 2. Legitimate variable resolution works
    assert ctx.resolve_expression("{{input.safe_key}}") == "safe_val"
    assert ctx.resolve_expression("{{variables.var_1}}") == "123"

def test_secret_redaction_in_execution_inputs(db_session: Session, sec_setup):
    """Verify sensitive credentials are automatically redacted from stored execution records."""
    user = sec_setup["user"]
    ws = sec_setup["ws"]

    wf_service = WorkflowService(db_session)
    exec_service = WorkflowExecutionService(db_session)

    wf = wf_service.create_workflow(
        user.id,
        ws.id,
        WorkflowCreate(
            name="Secret Ingestion",
            nodes=[
                WorkflowNodeCreate(node_key="start_1", node_type=WorkflowNodeType.START, name="Start"),
                WorkflowNodeCreate(node_key="end_1", node_type=WorkflowNodeType.END, name="End")
            ],
            edges=[
                WorkflowEdgeCreate(source_node_key="start_1", target_node_key="end_1")
            ]
        )
    )

    sensitive_input = {
        "user_name": "Alice",
        "api_key": "sk-live-super-secret-token-12345",
        "password": "Password987!",
        "auth_token": "Bearer abcxyz.jwt.token"
    }

    execution = exec_service.execute_workflow(user.id, ws.id, wf.id, input_data=sensitive_input)
    assert execution.status == WorkflowExecutionStatus.COMPLETED

    # DB record must have redacted sensitive keys
    db_session.refresh(execution)
    stored_input = execution.input_data
    assert stored_input["user_name"] == "Alice"
    assert stored_input["api_key"] == "[REDACTED]"
    assert stored_input["password"] == "[REDACTED]"
    assert stored_input["auth_token"] == "[REDACTED]"
