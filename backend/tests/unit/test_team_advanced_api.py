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
def p92_api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="P92 API Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, admin_role, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="P92 API Workspace")
    user1 = User(id=uuid.uuid4(), email="p92_owner@test.com", username="p92_owner", password_hash="h", role_id=admin_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="p92_member@test.com", username="p92_member", password_hash="h", role_id=user_role.id, is_active=True)
    
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    
    user1.role = admin_role
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

def test_p92_api_endpoints_e2e(p92_api_client):
    client, user2, ws = p92_api_client
    
    # 1. Create team
    res_c = client.post("/api/v1/teams", json={"name": "API Advanced Team"})
    assert res_c.status_code == 201
    team_id = res_c.json()["id"]
    
    # 2. Add user2 as member
    res_add = client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": str(user2.id), "role": "member"})
    assert res_add.status_code == 201
    
    # 3. Transfer ownership to user2
    res_trans = client.post(f"/api/v1/teams/{team_id}/transfer-ownership", json={"target_user_id": str(user2.id)})
    assert res_trans.status_code == 200
    assert res_trans.json()["owner_id"] == str(user2.id)
    
    # 4. Get eligible members
    res_elig = client.get(f"/api/v1/teams/{team_id}/eligible-members")
    assert res_elig.status_code == 200
    assert res_elig.json()["total"] == 0 # both user1 and user2 are members
    
    # 5. Archive team
    res_arch = client.post(f"/api/v1/teams/{team_id}/archive")
    assert res_arch.status_code == 200
    assert res_arch.json()["status"] == "archived"
    
    # 6. Restore team
    res_rest = client.post(f"/api/v1/teams/{team_id}/restore")
    assert res_rest.status_code == 200
    assert res_rest.json()["status"] == "active"
    
    # 7. Create and revoke invitation
    res_inv = client.post(f"/api/v1/teams/{team_id}/invitations", json={"invited_email": "newbie@test.com", "role": "member"})
    assert res_inv.status_code == 201
    inv_id = res_inv.json()["id"]
    
    res_inv_list = client.get(f"/api/v1/teams/{team_id}/invitations")
    assert res_inv_list.status_code == 200
    assert res_inv_list.json()["total"] == 1
    
    res_rev = client.post(f"/api/v1/team-invitations/{inv_id}/revoke")
    assert res_rev.status_code == 200
