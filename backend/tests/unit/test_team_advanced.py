import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.services.team import TeamService

@pytest.fixture
def advanced_team_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Advanced Team Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Advanced Workspace")
    user1 = User(id=uuid.uuid4(), email="owner@test.com", username="owner_user", password_hash="h", role_id=role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="member@test.com", username="member_user", password_hash="h", role_id=role.id, is_active=True)
    user3 = User(id=uuid.uuid4(), email="outsider@test.com", username="outsider_user", password_hash="h", role_id=role.id, is_active=True)
    
    session.add_all([ws, user1, user2, user3])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user3.id, role="member"))
    session.commit()
    
    yield session
    session.close()

def test_team_archive_and_restore_lifecycle(advanced_team_db: Session):
    service = TeamService(advanced_team_db)
    ws = advanced_team_db.query(Workspace).first()
    user1 = advanced_team_db.query(User).filter(User.username == "owner_user").first()
    
    # 1. Create team
    team = service.create_team(workspace_id=ws.id, name="Core Infra", creator_id=user1.id)
    assert team.status == "active"
    
    # 2. Archive team
    archived = service.archive_team(workspace_id=ws.id, team_id=team.id, actor_id=user1.id)
    assert archived.status == "archived"
    
    # 3. Restore team
    restored = service.restore_team(workspace_id=ws.id, team_id=team.id, actor_id=user1.id)
    assert restored.status == "active"
    
    # 4. Idempotent restore on already active team
    restored_again = service.restore_team(workspace_id=ws.id, team_id=team.id, actor_id=user1.id)
    assert restored_again.status == "active"

def test_atomic_ownership_transfer(advanced_team_db: Session):
    service = TeamService(advanced_team_db)
    ws = advanced_team_db.query(Workspace).first()
    user1 = advanced_team_db.query(User).filter(User.username == "owner_user").first()
    user2 = advanced_team_db.query(User).filter(User.username == "member_user").first()
    
    team = service.create_team(workspace_id=ws.id, name="Security Squad", creator_id=user1.id)
    service.add_member(workspace_id=ws.id, team_id=team.id, user_id=user2.id, role="member")
    
    # Transfer ownership to user2
    transferred = service.transfer_ownership(workspace_id=ws.id, team_id=team.id, target_user_id=user2.id, actor_id=user1.id)
    assert transferred.owner_id == user2.id
    
    # Verify user1 is now member, user2 is owner
    m1 = advanced_team_db.query(TeamMembership).filter(TeamMembership.team_id == team.id, TeamMembership.user_id == user1.id).first()
    m2 = advanced_team_db.query(TeamMembership).filter(TeamMembership.team_id == team.id, TeamMembership.user_id == user2.id).first()
    assert m1.role == "member"
    assert m2.role == "owner"

def test_owner_removal_protection(advanced_team_db: Session):
    service = TeamService(advanced_team_db)
    ws = advanced_team_db.query(Workspace).first()
    user1 = advanced_team_db.query(User).filter(User.username == "owner_user").first()
    
    team = service.create_team(workspace_id=ws.id, name="Sole Owner Team", creator_id=user1.id)
    
    # Attempt to remove sole owner -> must fail 400
    with pytest.raises(HTTPException) as exc_info:
        service.remove_member(workspace_id=ws.id, team_id=team.id, user_id=user1.id)
    assert exc_info.value.status_code == 400
    assert "sole team owner" in exc_info.value.detail.lower()

def test_membership_reactivation_safe(advanced_team_db: Session):
    service = TeamService(advanced_team_db)
    ws = advanced_team_db.query(Workspace).first()
    user1 = advanced_team_db.query(User).filter(User.username == "owner_user").first()
    user2 = advanced_team_db.query(User).filter(User.username == "member_user").first()
    
    team = service.create_team(workspace_id=ws.id, name="Reactivation Team", creator_id=user1.id)
    service.add_member(workspace_id=ws.id, team_id=team.id, user_id=user2.id, role="member")
    
    # Remove member
    service.remove_member(workspace_id=ws.id, team_id=team.id, user_id=user2.id)
    
    # Reactivate member
    reactivated = service.add_member(workspace_id=ws.id, team_id=team.id, user_id=user2.id, role="member")
    assert reactivated.status == "active"
    
    # Verify count
    members = service.list_members(workspace_id=ws.id, team_id=team.id)
    assert members.total == 2
