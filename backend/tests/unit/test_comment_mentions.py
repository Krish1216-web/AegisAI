import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership
from app.services.comment import CommentService

@pytest.fixture
def mention_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Mention Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Mention Workspace")
    user1 = User(id=uuid.uuid4(), email="alice@test.com", username="alice", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="bob@test.com", username="bob", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Mention Project", status="active", created_by=user1.id)
    session.add(proj)
    session.flush()
    session.add(ProjectMembership(id=uuid.uuid4(), project_id=proj.id, user_id=user1.id, role="owner", status="active"))
    session.add(ProjectMembership(id=uuid.uuid4(), project_id=proj.id, user_id=user2.id, role="editor", status="active"))
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session, ws, proj, user1, user2
    session.close()

def test_mention_parsing_and_persistence(mention_db):
    session, ws, proj, user1, user2 = mention_db
    service = CommentService(session)
    
    # 1. Create comment with mention @bob
    c = service.create_comment(workspace_id=ws.id, author_id=user1.id, body="Hello @bob and @alice, please review!", project_id=proj.id)
    assert len(c.mentions) == 2
    mention_names = {m.username for m in c.mentions}
    assert "bob" in mention_names
    assert "alice" in mention_names
    
    # 2. Mentionable users directory
    mentionables = service.list_mentionable_users(workspace_id=ws.id, project_id=proj.id, search="bo")
    assert len(mentionables) == 1
    assert mentionables[0].username == "bob"
