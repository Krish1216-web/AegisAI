import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.workspace import WorkspaceService

@pytest.fixture
def ws_mgmt_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Mgmt Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Mgmt Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="owner", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="admin@test.com", username="admin", password_hash="h", role_id=user_role.id, is_active=True)
    user3 = User(id=uuid.uuid4(), email="member@test.com", username="member", password_hash="h", role_id=user_role.id, is_active=True)
    
    session.add_all([ws, user1, user2, user3])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="admin"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user3.id, role="member"))
    session.commit()
    
    user1.role = user_role
    user2.role = user_role
    user3.role = user_role
    
    yield session
    session.close()

def test_update_member_role_and_owner_protection(ws_mgmt_db: Session):
    service = WorkspaceService(ws_mgmt_db)
    ws = ws_mgmt_db.query(Workspace).first()
    owner = ws_mgmt_db.query(User).filter(User.username == "owner").first()
    admin_u = ws_mgmt_db.query(User).filter(User.username == "admin").first()
    member_u = ws_mgmt_db.query(User).filter(User.username == "member").first()
    
    # 1. Owner updates member to viewer -> success
    updated = service.update_workspace_member_role(ws.id, member_u.id, "viewer", actor_id=owner.id)
    assert updated.role == "viewer"
    
    # 2. Attempt to demote sole owner -> must fail 400
    with pytest.raises(HTTPException) as exc_info:
        service.update_workspace_member_role(ws.id, owner.id, "member", actor_id=owner.id)
    assert exc_info.value.status_code == 400
    assert "sole workspace owner" in exc_info.value.detail.lower()

def test_transfer_workspace_ownership(ws_mgmt_db: Session):
    service = WorkspaceService(ws_mgmt_db)
    ws = ws_mgmt_db.query(Workspace).first()
    owner = ws_mgmt_db.query(User).filter(User.username == "owner").first()
    admin_u = ws_mgmt_db.query(User).filter(User.username == "admin").first()
    
    # Transfer ownership to admin_u
    res = service.transfer_workspace_ownership(ws.id, admin_u.id, actor_id=owner.id)
    assert res.role == "owner"
    assert res.user_id == admin_u.id
    
    # Verify previous owner is now admin
    prev_owner_m = ws_mgmt_db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == owner.id
    ).first()
    assert prev_owner_m.role == "admin"
