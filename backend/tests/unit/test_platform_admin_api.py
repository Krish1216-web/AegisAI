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
def admin_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="API Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    session.add_all([org, admin_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="API Workspace")
    user = User(
        id=uuid.uuid4(),
        email="admin_api@test.com",
        username="admin_api_user",
        password_hash="hash",
        role_id=admin_role.id,
        is_active=True
    )
    session.add_all([ws, user])
    session.flush()
    
    wm = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner")
    session.add(wm)
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
    yield client
    app.dependency_overrides.clear()
    session.close()

def test_api_admin_overview(admin_client: TestClient):
    response = admin_client.get("/api/v1/admin/overview?time_window=24h")
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "active_capabilities" in data

def test_api_admin_users_pagination_and_search(admin_client: TestClient):
    response = admin_client.get("/api/v1/admin/users?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data

def test_api_admin_system_health(admin_client: TestClient):
    response = admin_client.get("/api/v1/admin/system-health")
    assert response.status_code == 200
    data = response.json()
    assert "subsystems" in data
    assert len(data["subsystems"]) > 0

def test_api_admin_security_posture(admin_client: TestClient):
    response = admin_client.get("/api/v1/admin/security-posture")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_isolation_enforced"] is True

def test_api_admin_export(admin_client: TestClient):
    payload = {
        "export_type": "usage",
        "format": "json",
        "time_window": "24h",
        "limit": 100
    }
    response = admin_client.post("/api/v1/admin/export", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["export_type"] == "usage"
    assert "content" in data
