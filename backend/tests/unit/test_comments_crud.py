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
def comment_crud_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Comment Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Comment Workspace")
    user1 = User(id=uuid.uuid4(), email="author@test.com", username="author_u", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Comment Project", status="active", created_by=user1.id)
    session.add(proj)
    session.commit()
    user1.role = user_role
    
    yield session, ws, proj, user1
    session.close()

def test_comment_creation_editing_soft_deletion(comment_crud_db):
    session, ws, proj, user = comment_crud_db
    service = CommentService(session)
    
    # 1. Create comment
    c = service.create_comment(workspace_id=ws.id, author_id=user.id, body="Initial comment body", project_id=proj.id)
    assert c.status == "active"
    assert c.body == "Initial comment body"
    assert c.author_name == "author_u"
    
    # 2. Update comment
    upd = service.update_comment(workspace_id=ws.id, comment_id=c.id, body="Edited comment body", actor_id=user.id)
    assert upd.body == "Edited comment body"
    assert upd.edited_at is not None
    
    # 3. Soft delete
    service.delete_comment(workspace_id=ws.id, comment_id=c.id, actor_id=user.id)
    
    # 4. List comments shows masked body
    listing = service.list_comments(workspace_id=ws.id, project_id=proj.id)
    assert listing.total == 1
    assert listing.comments[0].status == "deleted"
    assert listing.comments[0].body == "This comment was deleted."
