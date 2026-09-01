import uuid
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Workspace, Organization
from app.api.v1.endpoints.admin import _require_admin
from app.services.platform_admin import PlatformAdminService
from app.core.mcp.security import CredentialStore

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    org = Organization(id=uuid.uuid4(), name="Sec Org")
    admin_role = Role(id=uuid.uuid4(), name="admin")
    session.add_all([org, admin_role])
    session.flush()
    
    ws = Workspace(id=uuid.uuid4(), organization_id=org.id, name="Sec Workspace")
    user = User(
        id=uuid.uuid4(),
        email="sec@test.com",
        username="sec_user",
        password_hash="hash",
        role_id=admin_role.id,
        is_active=True
    )
    session.add_all([ws, user])
    session.commit()
    
    yield session
    session.close()

def test_admin_role_authorization_enforcement():
    viewer_user = MagicMock(spec=User)
    viewer_role = MagicMock(spec=Role)
    viewer_role.name = "viewer"
    viewer_role.permissions = []
    viewer_user.role = viewer_role
    
    with pytest.raises(HTTPException) as exc_info:
        _require_admin(viewer_user)
    assert exc_info.value.status_code == 403

    admin_user = MagicMock(spec=User)
    admin_role = MagicMock(spec=Role)
    admin_role.name = "admin"
    admin_role.permissions = []
    admin_user.role = admin_role
    
    _require_admin(admin_user)

def test_admin_secret_redaction_in_audit_and_exports(db: Session):
    service = PlatformAdminService(db)
    
    export_res = service.export_report(
        export_type="usage",
        fmt="json",
        time_window="24h"
    )
    
    assert export_res is not None
    assert "sk-" not in export_res.content
    assert "password" not in export_res.content.lower() or "[REDACTED]" in export_res.content

def test_admin_security_posture_metrics(db: Session):
    service = PlatformAdminService(db)
    ws = db.query(Workspace).first()
    posture = service.get_security_posture(ws.id)
    
    assert posture.tenant_isolation_enforced is True
    assert posture.rbac_posture == "STRICT"
    assert posture.confirmation_gate_active is True
    assert posture.secret_redaction_active is True
