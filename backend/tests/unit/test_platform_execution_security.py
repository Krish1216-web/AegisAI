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
from app.core.platform.capability import (
    CapabilityMetadata,
    CapabilityType,
    PlatformCapability,
    platform_capability_registry
)
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
def sec_exec_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Sec Exec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, viewer_role])
    db_session.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Exec Alpha")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Exec Beta")
    user_a = User(
        id=uuid.uuid4(),
        email="ua@test.com",
        username="ua",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user_b = User(
        id=uuid.uuid4(),
        email="ub@test.com",
        username="ub",
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

def test_cross_tenant_execution_denial(db_session: Session, sec_exec_setup):
    user_a = sec_exec_setup["user_a"]
    ws_a = sec_exec_setup["ws_a"]
    ws_b = sec_exec_setup["ws_b"]

    # Spoofed context attempting to execute in Workspace B while user belongs to Workspace A
    sec_ctx = SecurityContext(
        user_id=user_a.id,
        workspace_id=ws_a.id, # Caller's verified tenant
        user_role="admin"
    )
    context = PlatformContext(
        user_id=user_a.id,
        workspace_id=ws_b.id, # Attempting to target ws_b
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("echo.test", context, {"data": "hack_attempt"})

    assert res.status == LifecycleState.DENIED
    assert len(res.errors) >= 1
    assert "Cross-tenant" in res.errors[0]["message"]

def test_rbac_permission_denial(db_session: Session, sec_exec_setup):
    user_b = sec_exec_setup["user_b"]
    ws_b = sec_exec_setup["ws_b"]

    # Register restricted capability requiring specific permission
    restricted_meta = CapabilityMetadata(
        capability_id="restricted.admin.cap",
        capability_type=CapabilityType.REASONING,
        name="Admin Only Tool",
        description="High security admin tool",
        required_permissions={"admin:override"}
    )
    class DummyRestrictedCap(PlatformCapability):
        pass
    platform_capability_registry.register(DummyRestrictedCap(restricted_meta))

    sec_ctx = SecurityContext(
        user_id=user_b.id,
        workspace_id=ws_b.id,
        user_role="viewer",
        permissions=set() # Viewer has no admin:override
    )
    context = PlatformContext(
        user_id=user_b.id,
        workspace_id=ws_b.id,
        security_context=sec_ctx
    )

    service = PlatformExecutionService(db_session)
    res = service.execute("restricted.admin.cap", context, {})

    assert res.status == LifecycleState.DENIED
    assert "CAPABILITY_PERMISSION_DENIED" in res.errors[0]["code"]
