import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.audit import AuditLog, ActivityLog
from app.services.platform_admin import PlatformAdminService
from app.services.platform_execution import PlatformExecutionService
from app.core.platform.lifecycle import LifecycleState

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Admin Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    member_role = Role(id=uuid.uuid4(), name="member")
    session.add_all([org, admin_role, member_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Test Workspace")
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        username="admin_user",
        password_hash="hash",
        role_id=admin_role.id,
        is_active=True
    )
    session.add_all([ws, user])
    session.flush()
    
    wm = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner")
    session.add(wm)
    session.commit()
    
    yield session
    session.close()

def test_admin_overview_calculation(db: Session):
    service = PlatformAdminService(db)
    ws = db.query(Workspace).first()
    overview = service.get_admin_overview(workspace_id=ws.id, time_window="24h")
    
    assert overview is not None
    assert overview.total_users >= 1
    assert overview.total_workspaces >= 1
    assert overview.system_status in ["ONLINE", "DEGRADED", "UNAVAILABLE"]
    assert isinstance(overview.success_rate, float)

def test_admin_user_listing_and_filtering(db: Session):
    service = PlatformAdminService(db)
    user = db.query(User).first()
    
    # 1. List all users
    res = service.list_users(page=1, page_size=10)
    assert res.total >= 1
    assert any(u.id == user.id for u in res.users)
    
    # 2. Filter by search
    res_search = service.list_users(search="admin")
    assert any(u.username == user.username for u in res_search.users)
    
    # 3. Filter by active status
    res_active = service.list_users(is_active=True)
    assert all(u.is_active is True for u in res_active.users)

def test_admin_user_status_and_role_updates(db: Session):
    service = PlatformAdminService(db)
    user = db.query(User).first()
    actor_id = user.id
    
    # Toggle active status to false
    updated_user = service.update_user_status(user.id, False, actor_id, "Test suspension")
    assert updated_user is not None
    assert updated_user.is_active is False
    
    # Check audit log was written
    audit = db.query(AuditLog).filter(AuditLog.action == "USER_SUSPENDED").first()
    assert audit is not None
    assert "Test suspension" in audit.details
    
    # Toggle active status back to true
    service.update_user_status(user.id, True, actor_id, "Reactivation")
    
    # Update role
    service.update_user_role(user.id, "admin", actor_id)
    assert user.role.name == "admin"

def test_admin_workspace_listing_and_counts(db: Session):
    service = PlatformAdminService(db)
    ws = db.query(Workspace).first()
    res = service.list_workspaces(page=1, page_size=10)
    assert res.total >= 1
    target = next((w for w in res.workspaces if w.id == ws.id), None)
    assert target is not None
    assert target.name == ws.name

def test_admin_system_health_diagnostics(db: Session):
    service = PlatformAdminService(db)
    health = service.get_system_health()
    
    assert health.overall_status in ["ONLINE", "DEGRADED", "UNAVAILABLE"]
    assert len(health.subsystems) >= 6
    sub_names = [s.name for s in health.subsystems]
    assert any("Database" in n for n in sub_names)
    assert any("Capability" in n for n in sub_names)
    assert any("Execution" in n for n in sub_names)
