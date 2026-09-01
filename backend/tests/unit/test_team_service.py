import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.team import TeamService

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Team Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Team Workspace")
    user = User(
        id=uuid.uuid4(),
        email="creator@test.com",
        username="creator_user",
        password_hash="hash",
        role_id=role.id,
        is_active=True
    )
    session.add_all([ws, user])
    session.flush()
    
    wm = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner")
    session.add(wm)
    session.commit()
    
    yield session
    session.close()

def test_create_and_get_team(db: Session):
    service = TeamService(db)
    ws = db.query(Workspace).first()
    user = db.query(User).first()
    
    team = service.create_team(
        workspace_id=ws.id,
        name="Alpha Engineering",
        description="Core platform engineers",
        creator_id=user.id
    )
    assert team is not None
    assert team.name == "Alpha Engineering"
    assert team.status == "active"
    assert team.member_count == 1 # Creator is auto-added as owner
    
    fetched = service.get_team(workspace_id=ws.id, team_id=team.id)
    assert fetched.id == team.id
    assert fetched.name == "Alpha Engineering"

def test_list_and_update_team(db: Session):
    service = TeamService(db)
    ws = db.query(Workspace).first()
    user = db.query(User).first()
    
    team = service.create_team(
        workspace_id=ws.id,
        name="Beta Ops",
        description="Operations",
        creator_id=user.id
    )
    
    # List teams
    res = service.list_teams(workspace_id=ws.id, status_filter="active")
    assert res.total >= 1
    assert any(t.id == team.id for t in res.teams)
    
    # Update team
    updated = service.update_team(
        workspace_id=ws.id,
        team_id=team.id,
        name="Beta Site Reliability",
        description="Updated ops",
        actor_id=user.id
    )
    assert updated.name == "Beta Site Reliability"
    assert updated.description == "Updated ops"

def test_archive_team(db: Session):
    service = TeamService(db)
    ws = db.query(Workspace).first()
    user = db.query(User).first()
    
    team = service.create_team(
        workspace_id=ws.id,
        name="Temporary Task Force",
        creator_id=user.id
    )
    assert team.status == "active"
    
    archived = service.archive_team(workspace_id=ws.id, team_id=team.id, actor_id=user.id)
    assert archived.status == "archived"
    
    # Verify active list excludes archived team by default
    active_list = service.list_teams(workspace_id=ws.id, status_filter="active")
    assert not any(t.id == team.id for t in active_list.teams)
