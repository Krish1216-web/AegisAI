import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.knowledge_bridge import KnowledgeContextBridge
from app.services.platform_execution import PlatformExecutionService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def know_sec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Knowledge Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, viewer_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Knowledge A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Knowledge B")
    user_a = User(
        id=uuid.uuid4(),
        email="uka@test.com",
        username="uka",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user_b = User(
        id=uuid.uuid4(),
        email="ukb@test.com",
        username="ukb",
        password_hash="pw",
        role_id=viewer_role.id,
        is_active=True
    )
    db_session.add_all([ws_a, ws_b, user_a, user_b])
    db_session.flush()

    mem_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_a.id, role="admin")
    mem_b = WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role="viewer")
    db_session.add_all([mem_a, mem_b])
    db_session.commit()

    return {"user_a": user_a, "user_b": user_b, "ws_a": ws_a, "ws_b": ws_b}

def test_cross_tenant_rag_denial(db_session: Session, know_sec_setup):
    user_a = know_sec_setup["user_a"]
    ws_a = know_sec_setup["ws_a"]
    ws_b = know_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_b.id, # Unauthorized cross-tenant attempt
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("knowledge.rag", context, {"query": "Find confidential data"})

    assert res.status == LifecycleState.DENIED
    assert len(res.errors) >= 1
    assert "Cross-tenant" in res.errors[0]["message"]

def test_cross_tenant_graph_denial(db_session: Session, know_sec_setup):
    user_a = know_sec_setup["user_a"]
    ws_a = know_sec_setup["ws_a"]
    ws_b = know_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_b.id,
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("knowledge.graph", context, {"entity": "TopSecretProject"})

    assert res.status == LifecycleState.DENIED

def test_rag_input_spoofing_defense(know_sec_setup):
    user_a = know_sec_setup["user_a"]
    ws_a = know_sec_setup["ws_a"]
    ws_b = know_sec_setup["ws_b"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        security_context=sec_ctx
    )

    malicious_input = {
        "query": "Security search",
        "workspace_id": str(ws_b.id),
        "user_id": str(uuid.uuid4())
    }

    params = KnowledgeContextBridge.platform_context_to_rag_query(context, malicious_input)

    assert params["workspace_id"] == ws_a.id
    assert params["workspace_id"] != ws_b.id
    assert params["user_id"] == user_a.id

def test_oversized_query_rejection(db_session: Session, know_sec_setup):
    user_a = know_sec_setup["user_a"]
    ws_a = know_sec_setup["ws_a"]

    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)

    # 3000 chars query exceeds 2000 limit
    oversized_query = "A" * 3000
    res = service.execute("knowledge.rag", context, {"query": oversized_query})

    assert res.status == LifecycleState.FAILED
    assert "INVALID_EXECUTION_INPUT" in res.errors[0]["code"]
