import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project
from app.models.comment import Comment
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_iso_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Iso Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS B")
    user_a = User(id=uuid.uuid4(), email="usera@iso.com", username="usera", password_hash="h", role_id=user_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="userb@iso.com", username="userb", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_a, ws_b, user_a, user_b])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner"))
    
    pa = Project(id=uuid.uuid4(), workspace_id=ws_a.id, name="Project in A", created_by=user_a.id, status="active")
    session.add(pa)
    session.flush()
    
    c_a = Comment(id=uuid.uuid4(), workspace_id=ws_a.id, project_id=pa.id, author_id=user_a.id, body="Comment in A")
    session.add(c_a)
    session.commit()
    
    yield session, ws_a, ws_b
    session.close()

def test_tenant_isolation_in_analytics(collab_iso_db):
    session, ws_a, ws_b = collab_iso_db
    service = CollaborationAnalyticsService(session)
    
    # Overview in Workspace A has 1 comment and 1 project
    res_a = service.get_overview(workspace_id=ws_a.id)
    assert res_a.total_comments == 1
    assert res_a.active_projects == 1
    
    # Overview in Workspace B has 0 comments and 0 projects
    res_b = service.get_overview(workspace_id=ws_b.id)
    assert res_b.total_comments == 0
    assert res_b.active_projects == 0
