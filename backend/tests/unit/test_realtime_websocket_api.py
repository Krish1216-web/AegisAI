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
from app.core.security import create_access_token

@pytest.fixture
def rt_api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="RT API Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="RT API Workspace")
    user1 = User(id=uuid.uuid4(), email="ws_user@test.com", username="ws_user", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.commit()
    user1.role = user_role
    
    token = create_access_token(subject=str(user1.id), roles=["user"], permissions=["workspace:view"])
    
    def override_get_db():
        db_s = SessionLocal()
        try:
            yield db_s
        finally:
            db_s.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client, token, ws
    app.dependency_overrides.clear()
    session.close()

def test_websocket_connection_and_ping_pong(rt_api_client):
    client, token, ws = rt_api_client
    
    # Connect with valid JWT token
    with client.websocket_connect(f"/api/v1/ws?token={token}") as websocket:
        # Expect connected welcome & presence
        msg1 = websocket.receive_json()
        assert msg1["type"] in ["connected", "presence"]
        
        msg2 = websocket.receive_json()
        assert msg2["type"] in ["connected", "presence"]
        
        # Ping -> Pong
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong["type"] == "pong"
