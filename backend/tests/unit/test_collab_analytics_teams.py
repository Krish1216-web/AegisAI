import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.services.collaboration_analytics import CollaborationAnalyticsService

@pytest.fixture
def collab_team_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Team Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Team Workspace")
    user = User(id=uuid.uuid4(), email="teamuser@test.com", username="teamuser", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, user])
    session.flush()
    
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=user.id, role="owner"))
    
    team = Team(id=uuid.uuid4(), workspace_id=ws.id, name="Alpha Team", created_by=user.id, status="active")
    session.add(team)
    session.flush()
    
    session.add(TeamMembership(id=uuid.uuid4(), team_id=team.id, user_id=user.id, role="owner"))
    session.commit()
    
    yield session, ws, team
    session.close()

def test_team_analytics_listing_and_health(collab_team_db):
    session, ws, team = collab_team_db
    service = CollaborationAnalyticsService(session)
    
    res = service.get_team_analytics(workspace_id=ws.id)
    assert res.total == 1
    assert len(res.teams) == 1
    t = res.teams[0]
    assert t.team_name == "Alpha Team"
    assert t.member_count == 1
    assert t.health_status == "HEALTHY"
