import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.api.v1.endpoints.teams import _assert_can_manage_team
from app.models.team import Team, TeamMembership

@pytest.fixture
def rbac_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="RBAC Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, admin_role, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="RBAC Workspace")
    
    sys_admin = User(id=uuid.uuid4(), email="admin@test.com", username="sys_admin", password_hash="h", role_id=admin_role.id, is_active=True)
    ws_owner = User(id=uuid.uuid4(), email="owner@test.com", username="ws_owner", password_hash="h", role_id=user_role.id, is_active=True)
    ws_member = User(id=uuid.uuid4(), email="member@test.com", username="ws_member", password_hash="h", role_id=user_role.id, is_active=True)
    ws_viewer = User(id=uuid.uuid4(), email="viewer@test.com", username="ws_viewer", password_hash="h", role_id=user_role.id, is_active=True)
    
    session.add_all([ws, sys_admin, ws_owner, ws_member, ws_viewer])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_owner.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_member.id, role="member"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=ws_viewer.id, role="viewer"))
    
    sys_admin.role = admin_role
    ws_owner.role = user_role
    ws_member.role = user_role
    ws_viewer.role = user_role
    
    session.commit()
    yield session
    session.close()

def test_rbac_team_management_permissions(rbac_db: Session):
    ws = rbac_db.query(Workspace).first()
    sys_admin = rbac_db.query(User).filter(User.username == "sys_admin").first()
    ws_owner = rbac_db.query(User).filter(User.username == "ws_owner").first()
    ws_member = rbac_db.query(User).filter(User.username == "ws_member").first()
    ws_viewer = rbac_db.query(User).filter(User.username == "ws_viewer").first()
    
    team = Team(id=uuid.uuid4(), workspace_id=ws.id, name="RBAC Team", status="active", created_by=ws_owner.id)
    rbac_db.add(team)
    rbac_db.commit()
    
    # 1. System admin should pass
    _assert_can_manage_team(ws.id, sys_admin, team.id, rbac_db)
    
    # 2. Workspace owner should pass
    _assert_can_manage_team(ws.id, ws_owner, team.id, rbac_db)
    
    # 3. Regular workspace member (not team owner) should be denied
    with pytest.raises(HTTPException) as exc_info:
        _assert_can_manage_team(ws.id, ws_member, team.id, rbac_db)
    assert exc_info.value.status_code == 403

    # 4. Workspace viewer should be denied
    with pytest.raises(HTTPException) as exc_info:
        _assert_can_manage_team(ws.id, ws_viewer, team.id, rbac_db)
    assert exc_info.value.status_code == 403
