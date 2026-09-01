import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database.base_class import Base
from app.database.session import get_db
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.main import app
from app.api.dependencies import get_current_user

@pytest.fixture
def project_api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Project API Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Project API Workspace")
    user1 = User(id=uuid.uuid4(), email="ws_owner@test.com", username="ws_owner", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="ws_collab@test.com", username="ws_collab", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    
    user1.role = user_role
    user1.workspace_id = ws.id
    
    def override_get_db():
        db_s = SessionLocal()
        try:
            yield db_s
        finally:
            db_s.close()
            
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user1
    
    client = TestClient(app)
    yield client, user2, ws
    app.dependency_overrides.clear()
    session.close()

def test_project_api_crud_flow(project_api_client):
    client, user2, ws = project_api_client
    
    # 1. Create project
    res_create = client.post(f"/api/v1/projects?workspace_id={ws.id}", json={"name": "API Project", "description": "API desc"})
    assert res_create.status_code == 201
    proj_id = res_create.json()["id"]
    
    # 2. List projects
    res_list = client.get(f"/api/v1/projects?workspace_id={ws.id}")
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1
    
    # 3. Add member
    res_add = client.post(f"/api/v1/projects/{proj_id}/members?workspace_id={ws.id}", json={"user_id": str(user2.id), "role": "editor"})
    assert res_add.status_code == 201
    
    # 4. List members
    res_mems = client.get(f"/api/v1/projects/{proj_id}/members?workspace_id={ws.id}")
    assert res_mems.status_code == 200
    assert res_mems.json()["total"] == 2
