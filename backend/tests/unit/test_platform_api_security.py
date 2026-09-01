import pytest
import uuid
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database.session import get_db
from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.api.v1.endpoints.auth import get_current_user
from app.core.platform.execution_result import PlatformExecutionResult
from app.core.platform.lifecycle import LifecycleState
from app.services.platform_execution import PlatformExecutionService

@pytest.fixture
def api_sec_setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="API Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db.add_all([org, admin_role, viewer_role])
    db.flush()

    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS API Sec A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS API Sec B")
    
    user_admin = User(
        id=uuid.uuid4(),
        email="admin_sec@test.com",
        username="admin_sec",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user_admin.workspace_id = ws_a.id
    user_admin.role = admin_role

    user_unauth = User(
        id=uuid.uuid4(),
        email="unauth@test.com",
        username="unauth",
        password_hash="pw",
        role_id=viewer_role.id,
        is_active=True
    )
    user_unauth.workspace_id = None
    user_unauth.role = viewer_role

    db.add_all([ws_a, ws_b, user_admin, user_unauth])
    db.flush()

    mem_a = WorkspaceMember(workspace_id=ws_a.id, user_id=user_admin.id, role="admin")
    db.add(mem_a)
    db.commit()

    # Seed an execution in Workspace A
    now = datetime.datetime.now(datetime.timezone.utc)
    ex = PlatformExecutionResult(
        execution_id="exec_sec_api_101",
        capability_id="knowledge.rag",
        status=LifecycleState.COMPLETED,
        output={"answer": "42"},
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=50),
        duration_ms=50.0,
        correlation_id="corr_sec_api_1",
        metadata={"workspace_id": str(ws_a.id)}
    )
    PlatformExecutionService._executions[ex.execution_id] = ex

    def override_get_db():
        try:
            yield db
        finally:
            pass

    current_user_holder = [user_admin]
    def override_get_current_user():
        return current_user_holder[0]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield {
        "client": client,
        "user_admin": user_admin,
        "user_unauth": user_unauth,
        "viewer_role": viewer_role,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "db": db,
        "current_user_holder": current_user_holder,
        "execution": ex
    }

    app.dependency_overrides.clear()
    db.close()

def test_missing_workspace_access_denial(api_sec_setup):
    client = api_sec_setup["client"]
    # Switch current user to user without active workspace
    api_sec_setup["current_user_holder"][0] = api_sec_setup["user_unauth"]

    res = client.get("/api/v1/platform/analytics/overview")
    assert res.status_code == 400
    assert "not associated with an active workspace" in res.json()["detail"]

def test_idor_cross_tenant_timeline_denial(api_sec_setup):
    client = api_sec_setup["client"]
    ws_b = api_sec_setup["ws_b"].id

    # Create a user in Workspace B
    user_b = User(
        id=uuid.uuid4(),
        email="user_b_sec@test.com",
        username="user_b_sec",
        password_hash="pw",
        role_id=api_sec_setup["viewer_role"].id,
        is_active=True
    )
    user_b.workspace_id = ws_b
    user_b.role = api_sec_setup["viewer_role"]
    api_sec_setup["current_user_holder"][0] = user_b

    # Attempt to access Workspace A's execution timeline
    ex_id = api_sec_setup["execution"].execution_id
    res = client.get(f"/api/v1/platform/analytics/executions/{ex_id}/timeline")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_fuzz_and_boundary_payload_handling(api_sec_setup):
    client = api_sec_setup["client"]
    api_sec_setup["current_user_holder"][0] = api_sec_setup["user_admin"]

    # Extremely long string
    long_query = "A" * 10000
    res = client.post("/api/v1/platform/intelligence/execute", json={
        "query": long_query,
        "mode": "adaptive"
    })
    # Should safely process or reject without 500 crash
    assert res.status_code in [200, 400, 422]

    # Malformed JSON payload
    res_malformed = client.post(
        "/api/v1/platform/intelligence/execute",
        content="{\"query\": incomplete_json",
        headers={"Content-Type": "application/json"}
    )
    assert res_malformed.status_code == 422

    # Invalid enum mode
    res_enum = client.post("/api/v1/platform/intelligence/execute", json={
        "query": "test",
        "mode": "invalid_mode_xyz"
    })
    assert res_enum.status_code == 422
