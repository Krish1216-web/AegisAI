import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.audit import AuditLog
from app.services.project import ProjectService

@pytest.fixture
def proj_audit_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Audit Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Audit Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="owner_aud", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user1])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.commit()
    user1.role = user_role
    
    yield session
    session.close()

def test_project_audit_trail_logging(proj_audit_db: Session):
    service = ProjectService(proj_audit_db)
    ws = proj_audit_db.query(Workspace).first()
    owner = proj_audit_db.query(User).filter(User.username == "owner_aud").first()
    
    # Create project -> PROJECT_CREATED
    proj = service.create_project(workspace_id=ws.id, name="Audit Trail Project", description=None, creator_id=owner.id)
    audit = proj_audit_db.query(AuditLog).filter(AuditLog.action == "PROJECT_CREATED").first()
    assert audit is not None
    assert "Audit Trail Project" in audit.details
