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
def comment_iso_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Comment Iso Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace A")
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace B")
    user_a = User(id=uuid.uuid4(), email="usera@test.com", username="usera", password_hash="h", role_id=user_role.id, is_active=True)
    user_b = User(id=uuid.uuid4(), email="userb@test.com", username="userb", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws_a, ws_b, user_a, user_b])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner"))
    
    proj_a = Project(id=uuid.uuid4(), workspace_id=ws_a.id, name="Project A", status="active", created_by=user_a.id)
    session.add(proj_a)
    session.commit()
    user_a.role = user_role
    user_b.role = user_role
    
    yield session, ws_a, ws_b, proj_a, user_a, user_b
    session.close()

def test_cross_tenant_comment_creation_denial(comment_iso_db):
    session, ws_a, ws_b, proj_a, user_a, user_b = comment_iso_db
    service = CommentService(session)
    
    # User B attempting to post to Workspace A's project under Workspace B context -> 404
    with pytest.raises(HTTPException) as exc_info:
        service.create_comment(workspace_id=ws_b.id, author_id=user_b.id, body="Cross tenant comment", project_id=proj_a.id)
    assert exc_info.value.status_code == 404
