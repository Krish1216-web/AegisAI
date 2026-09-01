import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project
from app.services.comment import CommentService

@pytest.fixture
def thread_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Thread Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Thread Workspace")
    user1 = User(id=uuid.uuid4(), email="thread@test.com", username="thread_u", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Thread Project", status="active", created_by=user1.id)
    session.add(proj)
    session.commit()
    user1.role = user_role
    
    yield session, ws, proj, user1
    session.close()

def test_comment_reply_and_hierarchy(thread_db):
    session, ws, proj, user = thread_db
    service = CommentService(session)
    
    # 1. Root comment
    root = service.create_comment(workspace_id=ws.id, author_id=user.id, body="Root topic", project_id=proj.id)
    
    # 2. Reply to root
    reply = service.create_comment(workspace_id=ws.id, author_id=user.id, body="Reply to root", project_id=proj.id, parent_comment_id=root.id)
    assert reply.parent_comment_id == root.id
    
    # 3. List comments showing replies
    comments = service.list_comments(workspace_id=ws.id, project_id=proj.id)
    assert comments.total == 2
    root_item = next(c for c in comments.comments if c.id == root.id)
    assert root_item.reply_count == 1
