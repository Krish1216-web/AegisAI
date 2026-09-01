import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.project import Project, ProjectMembership
from app.core.collaboration.realtime import RealtimeConnectionManager

@pytest.fixture
def rt_auth_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="RT Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="RT Workspace")
    user1 = User(id=uuid.uuid4(), email="rt_user@test.com", username="rt_user", password_hash="h", role_id=user_role.id, is_active=True)
    user_ext = User(id=uuid.uuid4(), email="ext@test.com", username="ext", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user_ext])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="member"))
    
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="RT Project", status="active", created_by=user1.id)
    session.add(proj)
    session.flush()
    session.add(ProjectMembership(id=uuid.uuid4(), project_id=proj.id, user_id=user1.id, role="editor", status="active"))
    session.commit()
    user1.role = user_role
    
    yield session, ws, proj, user1, user_ext
    session.close()

def test_channel_authorization_checks(rt_auth_db):
    session, ws, proj, user, user_ext = rt_auth_db
    manager = RealtimeConnectionManager()
    
    conn = manager.register_connection("conn_auth", user.id, ws.id, "rt_user")
    
    # 1. Authorize project subscription for member -> Success
    success, err = manager.authorize_and_subscribe("conn_auth", f"project:{proj.id}", session)
    assert success is True
    assert err is None
    assert f"project:{proj.id}" in conn.subscriptions
    
    # 2. Authorize invalid channel format -> Denied
    success_inv, err_inv = manager.authorize_and_subscribe("conn_auth", "invalid_channel_no_colon", session)
    assert success_inv is False
    assert "Invalid channel format" in err_inv
