import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.audit import AuditLog
from app.services.workspace import WorkspaceService

@pytest.fixture
def rbac_audit_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Audit Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Audit Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="owner_aud", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="member@test.com", username="member_aud", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    
    user1.role = user_role
    user2.role = user_role
    
    yield session
    session.close()

def test_rbac_audit_trail_logging(rbac_audit_db: Session):
    service = WorkspaceService(rbac_audit_db)
    ws = rbac_audit_db.query(Workspace).first()
    user1 = rbac_audit_db.query(User).filter(User.username == "owner_aud").first()
    user2 = rbac_audit_db.query(User).filter(User.username == "member_aud").first()
    
    # 1. Role Change -> WORKSPACE_ROLE_CHANGED
    service.update_workspace_member_role(ws.id, user2.id, "admin", actor_id=user1.id)
    audit_role = rbac_audit_db.query(AuditLog).filter(AuditLog.action == "WORKSPACE_ROLE_CHANGED").first()
    assert audit_role is not None
    assert "admin" in audit_role.details
    
    # 2. Transfer Ownership -> WORKSPACE_OWNER_TRANSFERRED
    service.transfer_workspace_ownership(ws.id, user2.id, actor_id=user1.id)
    audit_trans = rbac_audit_db.query(AuditLog).filter(AuditLog.action == "WORKSPACE_OWNER_TRANSFERRED").first()
    assert audit_trans is not None
