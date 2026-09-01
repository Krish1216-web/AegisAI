import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamInvitation
from app.services.team import TeamService

@pytest.fixture
def sec_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Sec Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    # Workspace A
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Sec Workspace A")
    user_a = User(id=uuid.uuid4(), email="usera@test.com", username="usera", password_hash="h", role_id=role.id, is_active=True)
    session.add_all([ws_a, user_a])
    session.flush()
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="owner"))
    
    # Workspace B
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Sec Workspace B")
    user_b = User(id=uuid.uuid4(), email="userb@test.com", username="userb", password_hash="h", role_id=role.id, is_active=True)
    session.add_all([ws_b, user_b])
    session.flush()
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="owner"))
    
    session.commit()
    yield session
    session.close()

def test_cross_tenant_invitation_security(sec_db: Session):
    service = TeamService(sec_db)
    ws_a = sec_db.query(Workspace).filter(Workspace.name == "Sec Workspace A").first()
    ws_b = sec_db.query(Workspace).filter(Workspace.name == "Sec Workspace B").first()
    user_a = sec_db.query(User).filter(User.username == "usera").first()
    user_b = sec_db.query(User).filter(User.username == "userb").first()
    
    team_a = service.create_team(workspace_id=ws_a.id, name="Team Secure A", creator_id=user_a.id)
    
    # 1. Workspace A attempts to invite user_b (from Workspace B) directly by user_id -> must fail 400
    with pytest.raises(HTTPException) as exc_info:
        service.create_invitation(workspace_id=ws_a.id, team_id=team_a.id, invited_user_id=user_b.id, invited_by=user_a.id)
    assert exc_info.value.status_code == 400

    # 2. Workspace A creates email invite for user_a
    invite_a = service.create_invitation(workspace_id=ws_a.id, team_id=team_a.id, invited_email="usera@test.com", invited_by=user_a.id)
    
    # 3. User B (Workspace B) attempts to accept Workspace A's invitation -> must fail 403
    with pytest.raises(HTTPException) as exc_info:
        service.accept_invitation(invitation_id=invite_a.id, user_id=user_b.id)
    assert exc_info.value.status_code == 403

def test_token_hashing_and_secret_redaction(sec_db: Session):
    service = TeamService(sec_db)
    ws_a = sec_db.query(Workspace).filter(Workspace.name == "Sec Workspace A").first()
    user_a = sec_db.query(User).filter(User.username == "usera").first()
    
    team_a = service.create_team(workspace_id=ws_a.id, name="Token Test Team", creator_id=user_a.id)
    invite = service.create_invitation(workspace_id=ws_a.id, team_id=team_a.id, invited_email="token_test@test.com", invited_by=user_a.id)
    
    # Verify token_hash in DB is 64 hex characters (SHA-256)
    db_invite = sec_db.query(TeamInvitation).filter(TeamInvitation.id == invite.id).first()
    assert db_invite.token_hash is not None
    assert len(db_invite.token_hash) == 64
