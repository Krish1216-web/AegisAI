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
def api_test_setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="API Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    db.add_all([org, admin_role])
    db.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="API WS")
    user = User(
        id=uuid.uuid4(),
        email="api_user@test.com",
        username="api_user",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    user.workspace_id = ws.id
    db.add_all([ws, user])
    db.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db.add(mem)
    db.commit()

    # Seed execution
    now = datetime.datetime.now(datetime.timezone.utc)
    ex = PlatformExecutionResult(
        execution_id="exec_api_test_1",
        capability_id="knowledge.rag",
        status=LifecycleState.COMPLETED,
        output={"answer": "42"},
        started_at=now,
        completed_at=now + datetime.timedelta(milliseconds=100),
        duration_ms=100.0,
        correlation_id="corr_api_1",
        metadata={"workspace_id": str(ws.id)}
    )
    PlatformExecutionService._executions[ex.execution_id] = ex

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield {"client": client, "user": user, "ws": ws, "db": db, "execution": ex}

    app.dependency_overrides.clear()
    db.close()

def test_analytics_overview_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/overview?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "total_executions" in data
    assert "success_rate" in data
    assert data["time_window"] == "24h"

def test_analytics_capabilities_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/capabilities?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "total_capabilities" in data
    assert "items" in data

def test_analytics_lifecycle_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/lifecycle?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "stage_durations_ms" in data
    assert "status_distribution" in data

def test_analytics_failures_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/failures?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "total_failures" in data
    assert "failures_by_category" in data

def test_analytics_intelligence_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/intelligence?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "total_executions" in data
    assert "avg_confidence" in data

def test_analytics_provenance_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/provenance?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "total_evidence_items" in data
    assert "source_distribution" in data

def test_analytics_bottlenecks_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/bottlenecks?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "bottlenecks" in data

def test_analytics_alerts_endpoint(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/alerts?time_window=24h")
    assert res.status_code == 200
    data = res.json()
    assert "total_alerts" in data
    assert "alerts" in data

def test_analytics_timeline_endpoint(api_test_setup):
    client = api_test_setup["client"]
    ex_id = api_test_setup["execution"].execution_id
    res = client.get(f"/api/v1/platform/analytics/executions/{ex_id}/timeline")
    assert res.status_code == 200
    data = res.json()
    assert data["execution_id"] == ex_id
    assert len(data["events"]) >= 1

def test_analytics_invalid_time_window_rejection(api_test_setup):
    client = api_test_setup["client"]
    res = client.get("/api/v1/platform/analytics/overview?time_window=999d")
    assert res.status_code == 400
    assert "Invalid time window" in res.json()["detail"]
