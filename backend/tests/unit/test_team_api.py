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
def team_api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="API Team Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, admin_role, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="API Team Workspace")
    user = User(
        id=uuid.uuid4(),
        email="team_api@test.com",
        username="team_api_user",
        password_hash="hash",
        role_id=admin_role.id,
        is_active=True
    )
    user2 = User(
        id=uuid.uuid4(),
        email="team_member@test.com",
        username="team_member_user",
        password_hash="hash",
        role_id=user_role.id,
        is_active=True
    )
    session.add_all([ws, user, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    
    user.role = admin_role
    user.workspace_id = ws.id
    
    def override_get_db():
        db_s = SessionLocal()
        try:
            yield db_s
        finally:
            db_s.close()
            
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    client = TestClient(app)
    yield client, user2
    app.dependency_overrides.clear()
    session.close()

def test_api_teams_crud_lifecycle(team_api_client):
    client, user2 = team_api_client
    
    # 1. Create team
    res_create = client.post("/api/v1/teams", json={"name": "API Intelligence Team", "description": "AI engineers"})
    assert res_create.status_code == 201
    team_data = res_create.json()
    team_id = team_data["id"]
    assert team_data["name"] == "API Intelligence Team"
    
    # 2. List teams
    res_list = client.get("/api/v1/teams?page=1&page_size=10")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1
    
    # 3. Get team
    res_get = client.get(f"/api/v1/teams/{team_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == team_id
    
    # 4. Update team
    res_upd = client.put(f"/api/v1/teams/{team_id}", json={"name": "Updated Intelligence Team"})
    assert res_upd.status_code == 200
    assert res_upd.json()["name"] == "Updated Intelligence Team"
    
    # 5. Add member
    res_add_mem = client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": str(user2.id), "role": "member"})
    assert res_add_mem.status_code == 201
    assert res_add_mem.json()["user_id"] == str(user2.id)
    
    # 6. List members
    res_mems = client.get(f"/api/v1/teams/{team_id}/members")
    assert res_mems.status_code == 200
    assert res_mems.json()["total"] == 2
    
    # 7. Remove member
    res_rem = client.delete(f"/api/v1/teams/{team_id}/members/{user2.id}")
    assert res_rem.status_code == 200
    
    # 8. Archive team
    res_arch = client.post(f"/api/v1/teams/{team_id}/archive")
    assert res_arch.status_code == 200
    assert res_arch.json()["status"] == "archived"
