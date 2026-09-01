import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.team import TeamService

@pytest.fixture
def membership_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Membership Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Membership Workspace")
    user1 = User(id=uuid.uuid4(), email="u1@test.com", username="u1", password_hash="h", role_id=role.id, is_active=True)
    user2 = User(id=uuid.uuid4(), email="u2@test.com", username="u2", password_hash="h", role_id=role.id, is_active=True)
    non_ws_user = User(id=uuid.uuid4(), email="outsider@test.com", username="outsider", password_hash="h", role_id=role.id, is_active=True)
    
    session.add_all([ws, user1, user2, non_ws_user])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user1.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user2.id, role="member"))
    
    session.commit()
    yield session
    session.close()

def test_membership_lifecycle_and_invariants(membership_db: Session):
    service = TeamService(membership_db)
    ws = membership_db.query(Workspace).first()
    u1 = membership_db.query(User).filter(User.username == "u1").first()
    u2 = membership_db.query(User).filter(User.username == "u2").first()
    non_ws_user = membership_db.query(User).filter(User.username == "outsider").first()
    
    team = service.create_team(workspace_id=ws.id, name="Dev Team", creator_id=u1.id)
    
    # 1. Non-workspace user cannot be added to team
    with pytest.raises(HTTPException) as exc_info:
        service.add_member(workspace_id=ws.id, team_id=team.id, user_id=non_ws_user.id)
    assert exc_info.value.status_code == 400

    # 2. Add valid workspace user
    member_res = service.add_member(workspace_id=ws.id, team_id=team.id, user_id=u2.id, role="member")
    assert member_res.user_id == u2.id
    assert member_res.role == "member"
    assert member_res.status == "active"

    # 3. Duplicate active membership prevented
    with pytest.raises(HTTPException) as exc_info:
        service.add_member(workspace_id=ws.id, team_id=team.id, user_id=u2.id, role="member")
    assert exc_info.value.status_code == 409

    # 4. List members
    members_list = service.list_members(workspace_id=ws.id, team_id=team.id)
    assert members_list.total == 2

    # 5. Remove member
    removed = service.remove_member(workspace_id=ws.id, team_id=team.id, user_id=u2.id)
    assert removed is True

    # 6. Verify list reflects removed member
    members_after = service.list_members(workspace_id=ws.id, team_id=team.id)
    assert members_after.total == 1
