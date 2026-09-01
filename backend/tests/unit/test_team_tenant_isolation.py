import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.team import TeamService
from app.core.collaboration.access import CollaborationResourceAccessService

@pytest.fixture
def multi_tenant_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Multi Tenant Org")
    role = Role(id=uuid.uuid4(), name="user")
    session.add_all([org, role])
    session.flush()
    
    # Workspace A & User A
    ws_a = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace A")
    user_a = User(id=uuid.uuid4(), email="user_a@test.com", username="user_a", password_hash="h", role_id=role.id, is_active=True)
    session.add_all([ws_a, user_a])
    session.flush()
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_a.id, user_id=user_a.id, role="member"))
    
    # Workspace B & User B
    ws_b = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Workspace B")
    user_b = User(id=uuid.uuid4(), email="user_b@test.com", username="user_b", password_hash="h", role_id=role.id, is_active=True)
    session.add_all([ws_b, user_b])
    session.flush()
    session.add(WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_b.id, user_id=user_b.id, role="member"))
    
    session.commit()
    yield session
    session.close()

def test_cross_tenant_team_access_denial(multi_tenant_db: Session):
    service = TeamService(multi_tenant_db)
    ws_a = multi_tenant_db.query(Workspace).filter(Workspace.name == "Workspace A").first()
    ws_b = multi_tenant_db.query(Workspace).filter(Workspace.name == "Workspace B").first()
    user_a = multi_tenant_db.query(User).filter(User.username == "user_a").first()
    user_b = multi_tenant_db.query(User).filter(User.username == "user_b").first()
    
    # User A creates Team in Workspace A
    team_a = service.create_team(workspace_id=ws_a.id, name="Team Alpha", creator_id=user_a.id)
    
    # Workspace B tries to GET Team A -> Must 404
    with pytest.raises(HTTPException) as exc_info:
        service.get_team(workspace_id=ws_b.id, team_id=team_a.id)
    assert exc_info.value.status_code == 404

    # Workspace B tries to UPDATE Team A -> Must 404
    with pytest.raises(HTTPException) as exc_info:
        service.update_team(workspace_id=ws_b.id, team_id=team_a.id, name="Hacked Name")
    assert exc_info.value.status_code == 404

    # Workspace B tries to ARCHIVE Team A -> Must 404
    with pytest.raises(HTTPException) as exc_info:
        service.archive_team(workspace_id=ws_b.id, team_id=team_a.id)
    assert exc_info.value.status_code == 404

    # Workspace B tries to ADD User B to Team A -> Must 404
    with pytest.raises(HTTPException) as exc_info:
        service.add_member(workspace_id=ws_b.id, team_id=team_a.id, user_id=user_b.id)
    assert exc_info.value.status_code == 404

def test_cross_tenant_resource_sharing_denial(multi_tenant_db: Session):
    access_service = CollaborationResourceAccessService(multi_tenant_db)
    ws_a = multi_tenant_db.query(Workspace).filter(Workspace.name == "Workspace A").first()
    ws_b = multi_tenant_db.query(Workspace).filter(Workspace.name == "Workspace B").first()
    user_b = multi_tenant_db.query(User).filter(User.username == "user_b").first()
    
    # User B attempting to access resource in Workspace A
    allowed = access_service.check_access(
        workspace_id=ws_a.id,
        user_id=user_b.id,
        resource_type="workflow",
        resource_id="wf_123"
    )
    assert allowed is False
