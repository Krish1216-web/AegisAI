import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.project import Project, ProjectResource
from app.models.document import Document
from app.models.workflow import Workflow, WorkflowStatus
from app.services.project import ProjectService

@pytest.fixture
def proj_res_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Res Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Res Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="res_owner", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    
    doc = Document(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user1.id,
        filename="research_report.pdf",
        original_filename="research_report.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1024,
        checksum="cs",
        storage_path="path/to/doc",
        status="PROCESSED"
    )
    wf = Workflow(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=user1.id,
        name="Data Analysis Pipeline",
        status=WorkflowStatus.ACTIVE
    )
    session.add_all([doc, wf])
    session.commit()
    user1.role = user_role
    
    yield session, doc, wf
    session.close()

def test_resource_linking_and_unlinking_without_deletion(proj_res_db):
    session, doc, wf = proj_res_db
    service = ProjectService(session)
    ws = session.query(Workspace).first()
    owner = session.query(User).filter(User.username == "res_owner").first()
    
    proj = service.create_project(workspace_id=ws.id, name="Analytics Hub", description=None, creator_id=owner.id)
    
    # 1. Link document
    link_doc = service.link_resource(workspace_id=ws.id, project_id=proj.id, resource_type="document", resource_id=str(doc.id), actor_id=owner.id)
    assert link_doc.resource_name == "research_report.pdf"
    
    # 2. Link workflow
    link_wf = service.link_resource(workspace_id=ws.id, project_id=proj.id, resource_type="workflow", resource_id=str(wf.id), actor_id=owner.id)
    assert link_wf.resource_name == "Data Analysis Pipeline"
    
    # 3. Verify count
    resources = service.list_resources(workspace_id=ws.id, project_id=proj.id)
    assert resources.total == 2
    
    # 4. Unlink document
    service.unlink_resource(workspace_id=ws.id, project_id=proj.id, resource_type="document", resource_id=str(doc.id), actor_id=owner.id)
    
    # 5. Verify source document was NOT deleted
    remaining_doc = session.query(Document).filter(Document.id == doc.id).first()
    assert remaining_doc is not None
    assert remaining_doc.filename == "research_report.pdf"
