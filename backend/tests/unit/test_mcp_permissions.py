import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.mcp.mcp_security import (
    MCPSecurityService,
    MCPSecurityDecisionEnum,
    MCPSecurityReasonCode
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Perm Org")
    role_user = Role(id=uuid.uuid4(), name="User")
    role_admin = Role(id=uuid.uuid4(), name="Admin")
    session.add_all([org, role_user, role_admin])
    session.commit()

    u_user = User(id=uuid.uuid4(), email="perm_u@test.com", username="perm_u", password_hash="pw", role_id=role_user.id, is_active=True)
    u_admin = User(id=uuid.uuid4(), email="perm_a@test.com", username="perm_a", password_hash="pw", role_id=role_admin.id, is_active=True)
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Perm")
    session.add_all([u_user, u_admin, ws])
    session.commit()

    mem_user = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=u_user.id, role="member")
    mem_admin = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=u_admin.id, role="admin")
    session.add_all([mem_user, mem_admin])
    session.commit()

    yield session
    session.close()

def test_rbac_capability_and_management_permissions(db_session):
    u_user = db_session.query(User).filter_by(email="perm_u@test.com").first()
    u_admin = db_session.query(User).filter_by(email="perm_a@test.com").first()

    sec_service = MCPSecurityService(db_session)

    # 1. Standard user role capability permissions
    assert sec_service.check_rbac_permission(u_user, "mcp:tool:view") is True
    assert sec_service.check_rbac_permission(u_user, "mcp:tool:execute") is True
    assert sec_service.check_rbac_permission(u_user, "mcp:resource:view") is True
    assert sec_service.check_rbac_permission(u_user, "mcp:resource:read") is True
    assert sec_service.check_rbac_permission(u_user, "mcp:prompt:view") is True
    assert sec_service.check_rbac_permission(u_user, "mcp:prompt:render") is True

    # 2. Standard user cannot manage servers or capabilities
    assert sec_service.check_rbac_permission(u_user, "mcp:server:manage") is False
    assert sec_service.check_rbac_permission(u_user, "mcp:tool:manage") is False
    assert sec_service.check_rbac_permission(u_user, "mcp:admin") is False

    # 3. Admin role possesses all permissions
    assert sec_service.check_rbac_permission(u_admin, "mcp:tool:execute") is True
    assert sec_service.check_rbac_permission(u_admin, "mcp:server:manage") is True
    assert sec_service.check_rbac_permission(u_admin, "mcp:tool:manage") is True
    assert sec_service.check_rbac_permission(u_admin, "mcp:admin") is True
