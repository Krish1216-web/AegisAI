import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership, ProjectResource
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_proj_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Proj Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Proj Workspace")
    user = User(id=uuid.uuid4(), email="projuser@test.com", username="projuser", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner"))
    
    p = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Beta Project", created_by=user.id, status="active")
    session.add(p)
    session.flush()
    
    session.add(ProjectMembership(id=uuid.uuid4(), project_id=p.id, user_id=user.id, role="owner", status="active"))
    session.add(ProjectResource(id=uuid.uuid4(), workspace_id=ws.id, project_id=p.id, resource_type="document", resource_id=str(uuid.uuid4()), created_by=user.id))
    session.commit()
    
    yield session, ws, p
    session.close()

def test_project_analytics_listing_and_resources(collab_proj_db):
    session, ws, p = collab_proj_db
    service = CollaborationAnalyticsService(session)
    
    res = service.get_project_analytics(workspace_id=ws.id)
    assert res.total == 1
    assert len(res.projects) == 1
    item = res.projects[0]
    assert item.project_name == "Beta Project"
    assert item.member_count == 1
    assert item.resource_count == 1
