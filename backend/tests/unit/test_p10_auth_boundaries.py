import uuid
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.services.auth import AuthService
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import AegisBaseException

@pytest.fixture
def auth_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Auth Test Org")
    user_role = Role(id=uuid.uuid4(), name="User", description="User role")
    session.add_all([org, user_role])
    session.flush()

    active_user = User(
        id=uuid.uuid4(),
        email="active@example.com",
        username="activeuser",
        password_hash=get_password_hash("SecretPass123!"),
        role_id=user_role.id,
        is_active=True,
        is_verified=True
    )
    inactive_user = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        username="inactiveuser",
        password_hash=get_password_hash("SecretPass123!"),
        role_id=user_role.id,
        is_active=False,
        is_verified=False
    )
    session.add_all([active_user, inactive_user])
    session.commit()

    active_user.role = user_role
    inactive_user.role = user_role

    mock_redis = MagicMock()
    service = AuthService(session, mock_redis)

    yield session, service, active_user, inactive_user
    session.close()

def test_login_active_user_success(auth_test_db):
    session, service, active_user, inactive_user = auth_test_db
    res = service.login_user("active@example.com", "SecretPass123!")
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["token_type"] == "bearer"

def test_login_inactive_user_rejected(auth_test_db):
    session, service, active_user, inactive_user = auth_test_db
    with pytest.raises(AegisBaseException) as exc_info:
        service.login_user("inactive@example.com", "SecretPass123!")
    assert exc_info.value.code == "ACCOUNT_SUSPENDED"

def test_login_wrong_password_rejected(auth_test_db):
    session, service, active_user, inactive_user = auth_test_db
    with pytest.raises(AegisBaseException) as exc_info:
        service.login_user("active@example.com", "WrongPassword!")
    assert exc_info.value.code == "AUTHENTICATION_FAILED"

def test_login_nonexistent_user_rejected(auth_test_db):
    session, service, active_user, inactive_user = auth_test_db
    with pytest.raises(AegisBaseException) as exc_info:
        service.login_user("nobody@example.com", "Password123!")
    assert exc_info.value.code == "AUTHENTICATION_FAILED"

def test_token_rotation_invalid_token(auth_test_db):
    session, service, active_user, inactive_user = auth_test_db
    with pytest.raises(AegisBaseException) as exc_info:
        service.rotate_tokens("invalid.fake.jwt.token")
    assert exc_info.value.code == "TOKEN_ROTATION_FAILED"

def test_password_hash_boundaries():
    pwd = "MySuperSecurePassword123456!"
    hashed = get_password_hash(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password(pwd + "extra", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(pwd, "") is False
