import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.services.platform_admin import PlatformAdminService

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Analytics Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    session.add_all([org, admin_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Analytics Workspace")
    user = User(
        id=uuid.uuid4(),
        email="analytics@test.com",
        username="analytics_user",
        password_hash="hash",
        role_id=admin_role.id,
        is_active=True
    )
    session.add_all([ws, user])
    session.commit()
    
    yield session
    session.close()

def test_admin_bounded_time_windows(db: Session):
    service = PlatformAdminService(db)
    ws = db.query(Workspace).first()
    
    for window in ["1h", "24h", "7d", "30d"]:
        overview = service.get_admin_overview(workspace_id=ws.id, time_window=window)
        assert overview.time_window == window
        assert overview.total_users >= 1

def test_admin_report_exports_json_and_csv(db: Session):
    service = PlatformAdminService(db)
    ws = db.query(Workspace).first()
    
    json_export = service.export_report(
        export_type="executions",
        fmt="json",
        limit=50,
        workspace_id=ws.id
    )
    assert json_export.format == "json"
    assert isinstance(json_export.content, str)
    
    csv_export = service.export_report(
        export_type="executions",
        fmt="csv",
        limit=50,
        workspace_id=ws.id
    )
    assert csv_export.format == "csv"
    assert isinstance(csv_export.content, str)
