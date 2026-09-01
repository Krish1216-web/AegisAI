import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.services.platform_admin import PlatformAdminService
from app.services.platform_execution import PlatformExecutionService
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="E2E Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    session.add_all([org, admin_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="E2E Workspace")
    user = User(
        id=uuid.uuid4(),
        email="e2e_admin@test.com",
        username="e2e_admin_user",
        password_hash="hash",
        role_id=admin_role.id,
        is_active=True
    )
    session.add_all([ws, user])
    session.commit()
    
    yield session
    session.close()

def test_full_admin_e2e_lifecycle(db: Session):
    ws = db.query(Workspace).first()
    user = db.query(User).first()
    
    # 1. Execute capability as user
    exec_service = PlatformExecutionService(db)
    ctx = PlatformContext(
        workspace_id=ws.id,
        user_id=user.id,
        correlation_id=str(uuid.uuid4()),
        security_context=SecurityContext(
            user_id=user.id,
            workspace_id=ws.id,
            user_role="admin",
            trust_level=TrustLevel.HIGH
        )
    )
    
    exec_res = exec_service.execute(
        capability_id="echo.test",
        context=ctx,
        input_data={"message": "Admin E2E audit task"}
    )
    assert exec_res is not None
    assert exec_res.execution_id is not None
    
    # 2. Admin service inspects executions
    admin_service = PlatformAdminService(db)
    exec_list = admin_service.list_executions(
        workspace_id=ws.id,
        capability_id="echo.test"
    )
    assert exec_list.total >= 1
    assert any(e.execution_id == exec_res.execution_id for e in exec_list.executions)
    
    # 3. Admin service queries overview and activity feed
    overview = admin_service.get_admin_overview(workspace_id=ws.id)
    assert overview.total_executions >= 1
    
    feed = admin_service.get_activity_feed(workspace_id=ws.id)
    assert feed.total >= 1
