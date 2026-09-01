import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership
from app.services.project import ProjectService

@pytest.fixture
def proj_mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Mem Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Mem Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="p_owner", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="collab@test.com", username="p_collab", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session
    session.close()

def test_project_membership_lifecycle_and_transfer(proj_mem_db: Session):
    service = ProjectService(proj_mem_db)
    ws = proj_mem_db.query(Workspace).first()
    owner = proj_mem_db.query(User).filter(User.username == "p_owner").first()
    collab = proj_mem_db.query(User).filter(User.username == "p_collab").first()
    
    proj = service.create_project(workspace_id=ws.id, name="Collab Project", description=None, creator_id=owner.id)
    
    # 1. Add member
    mem = service.add_member(workspace_id=ws.id, project_id=proj.id, user_id=collab.id, role="editor", actor_id=owner.id)
    assert mem.role == "editor"
    
    # 2. Sole owner removal protection
    with pytest.raises(HTTPException) as exc_info:
        service.remove_member(workspace_id=ws.id, project_id=proj.id, user_id=owner.id, actor_id=owner.id)
    assert exc_info.value.status_code == 400
    assert "sole project owner" in exc_info.value.detail.lower()
    
    # 3. Ownership transfer
    transferred = service.transfer_ownership(workspace_id=ws.id, project_id=proj.id, target_user_id=collab.id, actor_id=owner.id)
    assert transferred.owner_id == collab.id
    
    # 4. Remove previous owner (who is now editor)
    service.remove_member(workspace_id=ws.id, project_id=proj.id, user_id=owner.id, actor_id=collab.id)
    
    # 5. Reactivate member
    reactivated = service.add_member(workspace_id=ws.id, project_id=proj.id, user_id=owner.id, role="viewer", actor_id=collab.id)
    assert reactivated.status == "active"
    assert reactivated.role == "viewer"
