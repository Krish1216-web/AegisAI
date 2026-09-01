import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.audit import AuditLog, ActivityLog
from app.services.team import TeamService

@pytest.fixture
def audit_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Audit Team Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Audit Team Workspace")
    user = User(id=uuid.uuid4(), email="auditor@test.com", username="auditor_user", password_hash="hash", role_id=role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="auditee@test.com", username="auditee_user", password_hash="hash", role_id=role.id, is_active=True)
    session.add_all([ws, user, user2])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.commit()
    
    yield session
    session.close()

def test_team_audit_trail_generation(audit_db: Session):
    service = TeamService(audit_db)
    ws = audit_db.query(Workspace).first()
    user = audit_db.query(User).filter(User.username == "auditor_user").first()
    user2 = audit_db.query(User).filter(User.username == "auditee_user").first()
    
    # 1. Create team -> TEAM_CREATED
    team = service.create_team(workspace_id=ws.id, name="Security Audit Team", creator_id=user.id)
    audit_create = audit_db.query(AuditLog).filter(AuditLog.action == "TEAM_CREATED").first()
    assert audit_create is not None
    assert "Security Audit Team" in audit_create.details
    
    # 2. Update team -> TEAM_UPDATED
    service.update_team(workspace_id=ws.id, team_id=team.id, name="SecOps Audit Team", actor_id=user.id)
    audit_update = audit_db.query(AuditLog).filter(AuditLog.action == "TEAM_UPDATED").first()
    assert audit_update is not None
    assert "SecOps Audit Team" in audit_update.details
    
    # 3. Add member -> TEAM_MEMBER_ADDED
    service.add_member(workspace_id=ws.id, team_id=team.id, user_id=user2.id, role="member", actor_id=user.id)
    audit_add = audit_db.query(AuditLog).filter(AuditLog.action == "TEAM_MEMBER_ADDED").first()
    assert audit_add is not None
    assert user2.username in audit_add.details
    
    # 4. Remove member -> TEAM_MEMBER_REMOVED
    service.remove_member(workspace_id=ws.id, team_id=team.id, user_id=user2.id, actor_id=user.id)
    audit_rem = audit_db.query(AuditLog).filter(AuditLog.action == "TEAM_MEMBER_REMOVED").first()
    assert audit_rem is not None
    
    # 5. Archive team -> TEAM_ARCHIVED
    service.archive_team(workspace_id=ws.id, team_id=team.id, actor_id=user.id)
    audit_arch = audit_db.query(AuditLog).filter(AuditLog.action == "TEAM_ARCHIVED").first()
    assert audit_arch is not None
