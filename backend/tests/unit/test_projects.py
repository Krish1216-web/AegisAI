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
def project_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Project Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Project Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="p_owner", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.commit()
    user1.role = user_role
    
    yield session
    session.close()

def test_project_crud_and_archival(project_db: Session):
    service = ProjectService(project_db)
    ws = project_db.query(Workspace).first()
    owner = project_db.query(User).filter(User.username == "p_owner").first()
    
    # 1. Create project
    proj = service.create_project(workspace_id=ws.id, name="Alpha Engine", description="Alpha desc", creator_id=owner.id)
    assert proj.status == "active"
    assert proj.owner_id == owner.id
    assert proj.member_count == 1
    
    # 2. Update project
    upd = service.update_project(workspace_id=ws.id, project_id=proj.id, name="Alpha Engine V2", description="Updated desc", actor_id=owner.id)
    assert upd.name == "Alpha Engine V2"
    
    # 3. Archive project
    archived = service.archive_project(workspace_id=ws.id, project_id=proj.id, actor_id=owner.id)
    assert archived.status == "archived"
    
    # 4. Restore project
    restored = service.restore_project(workspace_id=ws.id, project_id=proj.id, actor_id=owner.id)
    assert restored.status == "active"
