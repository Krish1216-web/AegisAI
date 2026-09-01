import uuid
import datetime
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
def invite_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Invite Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Invite Workspace")
    inviter = User(id=uuid.uuid4(), email="inviter@test.com", username="inviter", password_hash="h", role_id=role.id, is_active=True)
    invitee = User(id=uuid.uuid4(), email="invitee@test.com", username="invitee", password_hash="h", role_id=role.id, is_active=True)
    
    session.add_all([ws, inviter, invitee])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=inviter.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=invitee.id, role="member"))
    session.commit()
    
    yield session
    session.close()

def test_invitation_lifecycle_create_and_accept(invite_db: Session):
    service = TeamService(invite_db)
    ws = invite_db.query(Workspace).first()
    inviter = invite_db.query(User).filter(User.username == "inviter").first()
    invitee = invite_db.query(User).filter(User.username == "invitee").first()
    
    team = service.create_team(workspace_id=ws.id, name="Collaboration Team", creator_id=inviter.id)
    
    # 1. Create invitation
    invite = service.create_invitation(
        workspace_id=ws.id,
        team_id=team.id,
        invited_user_id=invitee.id,
        role="member",
        invited_by=inviter.id
    )
    assert invite.status == "pending"
    assert invite.invited_user_id == invitee.id
    
    # 2. Duplicate invite prevented
    with pytest.raises(HTTPException) as exc_info:
        service.create_invitation(workspace_id=ws.id, team_id=team.id, invited_user_id=invitee.id)
    assert exc_info.value.status_code == 409
    
    # 3. Accept invitation
    member = service.accept_invitation(invitation_id=invite.id, user_id=invitee.id)
    assert member.user_id == invitee.id
    assert member.status == "active"
    
    # 4. Double acceptance prevented
    with pytest.raises(HTTPException) as exc_info:
        service.accept_invitation(invitation_id=invite.id, user_id=invitee.id)
    assert exc_info.value.status_code == 400

def test_invitation_expiration_and_revocation(invite_db: Session):
    service = TeamService(invite_db)
    ws = invite_db.query(Workspace).first()
    inviter = invite_db.query(User).filter(User.username == "inviter").first()
    invitee = invite_db.query(User).filter(User.username == "invitee").first()
    
    team = service.create_team(workspace_id=ws.id, name="Expiry Team", creator_id=inviter.id)
    
    # Create invitation with negative expiry (expired)
    invite = service.create_invitation(
        workspace_id=ws.id,
        team_id=team.id,
        invited_user_id=invitee.id,
        invited_by=inviter.id,
        expires_days=-1
    )
    
    # Accept expired invitation -> must fail 400
    with pytest.raises(HTTPException) as exc_info:
        service.accept_invitation(invitation_id=invite.id, user_id=invitee.id)
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()
    
    # Revoke test
    invite2 = service.create_invitation(
        workspace_id=ws.id,
        team_id=team.id,
        invited_email="pending_revocation@test.com",
        invited_by=inviter.id,
        expires_days=7
    )
    revoked = service.revoke_invitation(workspace_id=ws.id, invitation_id=invite2.id, actor_id=inviter.id)
    assert revoked is True
