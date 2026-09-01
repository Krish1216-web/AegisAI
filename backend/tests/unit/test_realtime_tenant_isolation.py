import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.core.collaboration.realtime import RealtimeConnectionManager

@pytest.fixture
def rt_iso_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Iso Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace B")
    user_a = User(id=uuid.uuid4(), email="a@test.com", username="user_a", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_a, ws_b, user_a])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    session.commit()
    user_a.role = user_role
    
    yield session, ws_a, ws_b, user_a
    session.close()

def test_cross_tenant_subscription_denial(rt_iso_db):
    session, ws_a, ws_b, user_a = rt_iso_db
    manager = RealtimeConnectionManager()
    
    conn = manager.register_connection("conn_a", user_a.id, ws_a.id, "user_a")
    
    # Attempt to subscribe to Workspace B channel -> Denied
    success, err = manager.authorize_and_subscribe("conn_a", f"workspace:{ws_b.id}", session)
    assert success is False
    assert "Cross-workspace subscription denied" in err
