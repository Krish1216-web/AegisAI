import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.workspace import WorkspaceService
from app.services.authorization import AuthorizationService
from app.core.auth.permissions import Permissions

@pytest.fixture
def rbac_sec_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Sec RBAC Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    # Workspace A
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace A")
    user_a = User(id=uuid.uuid4(), email="usera@test.com", username="usera", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_a, user_a])
    session.flush()
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    
    # Workspace B
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace B")
    user_b = User(id=uuid.uuid4(), email="userb@test.com", username="userb", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_b, user_b])
    session.flush()
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="member"))
    
    session.commit()
    user_a.role = user_role
    user_b.role = user_role
    
    yield session
    session.close()

def test_cross_tenant_role_modification_denial(rbac_sec_db: Session):
    service = WorkspaceService(rbac_sec_db)
    ws_a = rbac_sec_db.query(Workspace).filter(Workspace.name == "Workspace A").first()
    ws_b = rbac_sec_db.query(Workspace).filter(Workspace.name == "Workspace B").first()
    user_b = rbac_sec_db.query(User).filter(User.username == "userb").first()
    
    # User B (from Workspace B) attempting to modify roles in Workspace A -> must fail 404
    with pytest.raises(HTTPException) as exc_info:
        service.update_workspace_member_role(ws_a.id, user_b.id, "owner", actor_id=user_b.id)
    assert exc_info.value.status_code == 404

def test_privilege_escalation_denial(rbac_sec_db: Session):
    service = WorkspaceService(rbac_sec_db)
    ws_b = rbac_sec_db.query(Workspace).filter(Workspace.name == "Workspace B").first()
    user_b = rbac_sec_db.query(User).filter(User.username == "userb").first()
    
    # Member user_b attempting to promote themselves to admin -> must fail 403
    with pytest.raises(HTTPException) as exc_info:
        service.update_workspace_member_role(ws_b.id, user_b.id, "admin", actor_id=user_b.id)
    assert exc_info.value.status_code == 403
