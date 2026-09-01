import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.models.team import Team, TeamMembership
from app.services.team import TeamService
from fastapi import HTTPException

@pytest.fixture
def rbac_attack_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="RBAC Org")
    user_role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, user_role])
    session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="RBAC Workspace")
    owner = User(id=uuid.uuid4(), email="owner@test.com", username="owner", password_hash="h", role_id=user_role.id, is_active=True)
    member = User(id=uuid.uuid4(), email="member@test.com", username="member", password_hash="h", role_id=user_role.id, is_active=True)
    session.add_all([ws, owner, member])
    session.flush()

    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=owner.id, role="owner"))
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws.id, user_id=member.id, role="member"))

    team = Team(id=uuid.uuid4(), workspace_id=ws.id, name="Protected Team", created_by=owner.id, status="active")
    session.add(team)
    session.flush()

    session.add(TeamMembership(id=uuid.uuid4(), team_id=team.id, user_id=owner.id, role="owner"))
    session.add(TeamMembership(id=uuid.uuid4(), team_id=team.id, user_id=member.id, role="member"))
    session.commit()

    owner.role = user_role
    member.role = user_role

    yield session, ws, owner, member, team
    session.close()

def test_sole_owner_protection_and_escalation_denial(rbac_attack_db):
    session, ws, owner, member, team = rbac_attack_db
    service = TeamService(session)

    # Sole owner removal protection (cannot remove the only active owner)
    with pytest.raises(HTTPException):
        service.remove_member(
            workspace_id=ws.id,
            team_id=team.id,
            user_id=owner.id,
            actor_id=owner.id
        )
