import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project
from app.services.comment import CommentService

@pytest.fixture
def activity_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Act Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Act Workspace")
    user1 = User(id=uuid.uuid4(), email="act_u@test.com", username="act_u", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Act Project", status="active", created_by=user1.id)
    session.add(proj)
    session.commit()
    user1.role = user_role
    
    yield session, ws, proj, user1
    session.close()

def test_activity_timeline_retrieval(activity_db):
    session, ws, proj, user = activity_db
    service = CommentService(session)
    
    # Create comment triggers activity log
    service.create_comment(workspace_id=ws.id, author_id=user.id, body="Activity comment", project_id=proj.id)
    
    # Retrieve timeline
    activity_res = service.list_activity(workspace_id=ws.id)
    assert activity_res.total >= 1
    assert any(a.activity_type == "COMMENT_CREATED" for a in activity_res.activities)
