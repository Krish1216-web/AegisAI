import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.services.authorization import AuthorizationService
from app.core.auth.permissions import Permissions

@pytest.fixture
def auth_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Auth Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, admin_role, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Auth Workspace")
    sys_admin = User(id=uuid.uuid4(), email="sys_admin@test.com", username="sys_admin", password_hash="h", role_id=admin_role.id, is_active=True)
    ws_owner = User(id=uuid.uuid4(), email="ws_owner@test.com", username="ws_owner", password_hash="h", role_id=user_role.id, is_active=True)
    ws_admin = User(id=uuid.uuid4(), email="ws_admin@test.com", username="ws_admin", password_hash="h", role_id=user_role.id, is_active=True)
    ws_member = User(id=uuid.uuid4(), email="ws_member@test.com", username="ws_member", password_hash="h", role_id=user_role.id, is_active=True)
    ws_viewer = User(id=uuid.uuid4(), email="ws_viewer@test.com", username="ws_viewer", password_hash="h", role_id=user_role.id, is_active=True)
    
    session.add_all([ws, sys_admin, ws_owner, ws_admin, ws_member, ws_viewer])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_owner.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_admin.id, role="admin"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_member.id, role="member"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_viewer.id, role="viewer"))
    session.commit()
    
    sys_admin.role = admin_role
    ws_owner.role = user_role
    ws_admin.role = user_role
    ws_member.role = user_role
    ws_viewer.role = user_role
    
    yield session
    session.close()

def test_effective_permissions_by_role(auth_db: Session):
    auth_service = AuthorizationService(auth_db)
    ws = auth_db.query(Workspace).first()
    sys_admin = auth_db.query(User).filter(User.username == "sys_admin").first()
    ws_owner = auth_db.query(User).filter(User.username == "ws_owner").first()
    ws_admin = auth_db.query(User).filter(User.username == "ws_admin").first()
    ws_member = auth_db.query(User).filter(User.username == "ws_member").first()
    ws_viewer = auth_db.query(User).filter(User.username == "ws_viewer").first()
    
    # 1. System Admin has all permissions
    admin_perms = auth_service.get_effective_permissions(sys_admin.id, ws.id)
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP in admin_perms
    assert Permissions.ADMIN_USERS_MANAGE in admin_perms
    
    # 2. Workspace Owner has workspace management & transfer ownership
    owner_perms = auth_service.get_effective_permissions(ws_owner.id, ws.id)
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP in owner_perms
    assert Permissions.WORKSPACE_ROLES_MANAGE in owner_perms
    
    # 3. Workspace Admin has roles manage but NOT transfer ownership
    ws_admin_perms = auth_service.get_effective_permissions(ws_admin.id, ws.id)
    assert Permissions.WORKSPACE_ROLES_MANAGE in ws_admin_perms
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP not in ws_admin_perms
    
    # 4. Workspace Member can create workflows & documents but cannot manage roles
    member_perms = auth_service.get_effective_permissions(ws_member.id, ws.id)
    assert Permissions.WORKFLOW_CREATE in member_perms
    assert Permissions.WORKSPACE_ROLES_MANAGE not in member_perms
    
    # 5. Workspace Viewer has read-only access
    viewer_perms = auth_service.get_effective_permissions(ws_viewer.id, ws.id)
    assert Permissions.WORKSPACE_VIEW in viewer_perms
    assert Permissions.WORKFLOW_CREATE not in viewer_perms

def test_team_role_permission_overlay(auth_db: Session):
    auth_service = AuthorizationService(auth_db)
    ws = auth_db.query(Workspace).first()
    ws_member = auth_db.query(User).filter(User.username == "ws_member").first()
    
    # Create Team
    team = Team(id=uuid.uuid4(), workspace_id=ws.id, name="Project Phoenix", status="active", created_by=ws_member.id)
    tm = TeamMembership(id=uuid.uuid4(), team_id=team.id, user_id=ws_member.id, role="owner", status="active")
    auth_db.add_all([team, tm])
    auth_db.commit()
    
    # Without team_id: standard member perms (no TEAM_UPDATE)
    base_perms = auth_service.get_effective_permissions(ws_member.id, ws.id)
    assert Permissions.TEAM_UPDATE not in base_perms
    
    # With team_id: team owner overlay grants TEAM_UPDATE & TEAM_MANAGE
    team_perms = auth_service.get_effective_permissions(ws_member.id, ws.id, team_id=team.id)
    assert Permissions.TEAM_UPDATE in team_perms
    assert Permissions.TEAM_MANAGE in team_perms
    # Still doesn't gain workspace-wide transfer ownership
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP not in team_perms
