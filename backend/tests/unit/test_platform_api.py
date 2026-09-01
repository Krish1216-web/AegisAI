import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization, WorkspaceMember
from app.services.platform_service import PlatformService
from app.core.platform.capability import CapabilityType

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def platform_setup(db_session: Session):
    org = Organization(id=uuid.uuid4(), name="Platform Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    viewer_role = Role(id=uuid.uuid4(), name="viewer")
    db_session.add_all([org, admin_role, viewer_role])
    db_session.flush()

    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="WS Platform")
    user = User(
        id=uuid.uuid4(),
        email="platform_user@test.com",
        username="platform_user",
        password_hash="pw",
        role_id=admin_role.id,
        is_active=True
    )
    db_session.add_all([ws, user])
    db_session.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="admin")
    db_session.add(mem)
    db_session.commit()

    return {"user": user, "ws": ws, "admin_role": admin_role, "viewer_role": viewer_role}

def test_platform_service_status_and_capabilities(db_session: Session, platform_setup):
    ws = platform_setup["ws"]
    user = platform_setup["user"]

    service = PlatformService(db_session)

    # 1. Platform Status
    status = service.get_platform_status(ws.id)
    assert status.version == "8.1.0"
    assert status.workspace_id == ws.id
    assert status.system_health == "HEALTHY"
    assert status.active_capabilities >= 6
    assert "Multi-Agent Orchestrator" in status.registered_subsystems
    assert "Visual Workflow & Composition Engine" in status.registered_subsystems

    # 2. List Capabilities
    caps = service.list_capabilities(ws.id, user_role="admin")
    assert caps.total >= 6
    cap_ids = [c.capability_id for c in caps.items]
    assert "agent.orchestrator" in cap_ids
    assert "rag.retriever" in cap_ids
    assert "workflow.engine" in cap_ids

    # 3. Filter by type
    wf_caps = service.list_capabilities(ws.id, user_role="admin", capability_type=CapabilityType.WORKFLOW)
    assert wf_caps.total == 1
    assert wf_caps.items[0].capability_id == "workflow.engine"

    # 4. Get specific capability
    cap = service.get_capability(ws.id, "mcp.platform")
    assert cap is not None
    assert cap.name == "Model Context Protocol Platform"

    # 5. Non-existent capability
    missing = service.get_capability(ws.id, "non.existent")
    assert missing is None
