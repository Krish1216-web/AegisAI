import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership
from app.services.comment import CommentService

@pytest.fixture
def comment_auth_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Auth Comment Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Auth Comment Workspace")
    user1 = User(id=uuid.uuid4(), email="user1@test.com", username="user1", password_hash="h", role_id=user_role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="user2@test.com", username="user2", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="member"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    
    proj = Project(id=uuid.uuid4(), workspace_id=ws.id, name="Auth Comment Project", status="active", created_by=user1.id)
    session.add(proj)
    session.commit()
    user1.role = user_role
    user2.role = user_role
    
    yield session, ws, proj, user1, user2
    session.close()

def test_comment_author_permission_enforcement(comment_auth_db):
    session, ws, proj, user1, user2 = comment_auth_db
    service = CommentService(session)
    
    # User 1 creates comment
    c = service.create_comment(workspace_id=ws.id, author_id=user1.id, body="User 1 comment", project_id=proj.id)
    
    # User 2 tries to edit User 1's comment -> Forbidden
    with pytest.raises(HTTPException) as exc_info:
        service.update_comment(workspace_id=ws.id, comment_id=c.id, body="Malicious edit", actor_id=user2.id)
    assert exc_info.value.status_code == 403
