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
def rbac_api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="RBAC API Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="RBAC API Workspace")
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

def test_rbac_api_endpoints_crud(rbac_api_client):
    client, user2, ws = rbac_api_client
    
    # 1. List workspace members
    res_mems = client.get(f"/api/v1/workspaces/{ws.id}/members")
    assert res_mems.status_code == 200
    assert res_mems.json()["total"] == 2
    
    # 2. Update member role to admin
    res_upd = client.put(f"/api/v1/workspaces/{ws.id}/members/{user2.id}/role", json={"role": "admin"})
    assert res_upd.status_code == 200
    assert res_upd.json()["role"] == "admin"
    
    # 3. Get effective permissions
    res_perms = client.get(f"/api/v1/workspaces/{ws.id}/effective-permissions")
    assert res_perms.status_code == 200
    perms_data = res_perms.json()
    assert perms_data["workspace_role"] == "owner"
    assert "workspace:transfer_ownership" in perms_data["permissions"]
    
    # 4. Get permissions registry
    res_reg = client.get("/api/v1/permissions")
    assert res_reg.status_code == 200
    assert len(res_reg.json()["permissions"]) >= 10
    
    # 5. Transfer ownership
    res_trans = client.post(f"/api/v1/workspaces/{ws.id}/transfer-ownership", json={"target_user_id": str(user2.id)})
    assert res_trans.status_code == 200
    assert res_trans.json()["role"] == "owner"
