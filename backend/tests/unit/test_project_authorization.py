import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership
from app.services.authorization import AuthorizationService
from app.core.auth.permissions import Permissions

@pytest.fixture
def proj_auth_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Auth Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Auth Workspace")
    user1 = User(id=uuid.uuid4(), email="ws_mem@test.com", username="ws_mem", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="member"))
    
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Scoped Project", status="active", created_by=user1.id)
    session.add(proj)
    session.flush()
    
    session.add(ProjectMembership(id=uuid.uuid4(), project_id=proj.id, user_id=user1.id, role="editor", status="active"))
    session.commit()
    user1.role = user_role
    
    yield session, ws, proj, user1
    session.close()

def test_project_role_effective_permissions(proj_auth_db):
    session, ws, proj, user = proj_auth_db
    auth_service = AuthorizationService(session)
    
    # 1. Base workspace member permissions (no project resource add)
    base_perms = auth_service.get_effective_permissions(user_id=user.id, workspace_id=ws.id)
    assert Permissions.PROJECT_RESOURCE_ADD not in base_perms
    
    # 2. With project overlay (editor role grants PROJECT_RESOURCE_ADD)
    proj_perms = auth_service.get_effective_permissions(user_id=user.id, workspace_id=ws.id, project_id=proj.id)
    assert Permissions.PROJECT_RESOURCE_ADD in proj_perms
    assert Permissions.PROJECT_RESOURCE_VIEW in proj_perms
    # Still does not gain workspace transfer ownership
    assert Permissions.WORKSPACE_TRANSFER_OWNERSHIP not in proj_perms
