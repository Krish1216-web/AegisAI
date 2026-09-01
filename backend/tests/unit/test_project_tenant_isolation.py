import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectMembership
from app.models.document import Document
from app.services.project import ProjectService

@pytest.fixture
def proj_iso_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Iso Org")
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
    
    doc_b = Document(
        id=uuid.uuid4(),
        workspace_id=ws_b.id,
        user_id=user_b.id,
        filename="secret_b.pdf",
        original_filename="secret_b.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1024,
        checksum="cs",
        storage_path="path/to/doc",
        status="PROCESSED"
    )
    session.add(doc_b)
    session.commit()
    user_a.role = user_role
    user_b.role = user_role
    
    yield session, ws_a, ws_b, user_a, user_b, doc_b
    session.close()

def test_cross_tenant_resource_linking_denial(proj_iso_db):
    session, ws_a, ws_b, user_a, user_b, doc_b = proj_iso_db
    service = ProjectService(session)
    
    proj_a = service.create_project(workspace_id=ws_a.id, name="Project Alpha", description=None, creator_id=user_a.id)
    
    # Attempt to link Workspace B's document to Workspace A's project -> must fail 404
    with pytest.raises(HTTPException) as exc_info:
        service.link_resource(workspace_id=ws_a.id, project_id=proj_a.id, resource_type="document", resource_id=str(doc_b.id), actor_id=user_a.id)
    assert exc_info.value.status_code == 404
