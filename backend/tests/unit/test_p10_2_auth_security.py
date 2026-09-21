import uuid
import pytest
import jwt
from unittest.mock import MagicMock
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base
from app.models.user import User, Role
from app.models.workspace import Organization, Workspace, WorkspaceMember
from app.models.audit import AuditLog
from app.services.auth import AuthService
from app.core.security import (
    get_password_hash,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.core.exceptions import AegisBaseException
from app.api.dependencies import get_current_user
from app.schemas.user import UserCreate


@pytest.fixture
def auth_sec_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    org = Organization(id=uuid.uuid4(), name="Sec Org")
    user_role = Role(id=uuid.uuid4(), name="User", description="Standard User")
    admin_role = Role(id=uuid.uuid4(), name="Admin", description="Admin User")
    session.add_all([org, user_role, admin_role])
    session.flush()

    active_user = User(
        id=uuid.uuid4(),
        email="user@aegis.enterprise",
        username="secuser",
        password_hash=get_password_hash("StrongPass123!"),
        role_id=user_role.id,
        is_active=True,
        is_verified=True,
        is_deleted=False,
    )
    suspended_user = User(
        id=uuid.uuid4(),
        email="suspended@aegis.enterprise",
        username="suspendeduser",
        password_hash=get_password_hash("StrongPass123!"),
        role_id=user_role.id,
        is_active=False,
        is_verified=True,
        is_deleted=False,
    )
    deleted_user = User(
        id=uuid.uuid4(),
        email="deleted@aegis.enterprise",
        username="deleteduser",
        password_hash=get_password_hash("StrongPass123!"),
        role_id=user_role.id,
        is_active=True,
        is_verified=True,
        is_deleted=True,
    )

    session.add_all([active_user, suspended_user, deleted_user])
    session.commit()

    active_user.role = user_role
    suspended_user.role = user_role
    deleted_user.role = user_role

    mock_redis = MagicMock()
    mock_redis.exists.return_value = 1
    mock_redis.hset.return_value = 1
    mock_redis.expire.return_value = 1
    mock_redis.delete.return_value = 1
    mock_redis.keys.return_value = [b"aegis:session:dummy"]

    service = AuthService(session, mock_redis)

    yield session, service, active_user, suspended_user, deleted_user, mock_redis
    session.close()


def test_password_strength_validator_rules():
    # Valid passwords
    valid, msg = validate_password_strength("ValidP@ssw0rd")
    assert valid is True

    # Short password
    valid, msg = validate_password_strength("Short1!")
    assert valid is False
    assert "at least 8 characters" in msg

    # Long password exceeding 128 chars
    valid, msg = validate_password_strength("A" * 129 + "1!")
    assert valid is False
    assert "must not exceed 128" in msg

    # Empty / whitespace
    valid, msg = validate_password_strength("   ")
    assert valid is False

    # Missing letters or numbers
    valid, msg = validate_password_strength("1234567890!")
    assert valid is False


def test_register_user_weak_password_rejected(auth_sec_db):
    session, service, active_user, _, _, _ = auth_sec_db
    # 8 chars but only letters -> fails complexity
    payload = UserCreate(
        email="newuser@aegis.enterprise",
        username="newuser",
        password="onlyletterspassword",
        role_name="User"
    )
    with pytest.raises(AegisBaseException) as exc_info:
        service.register_user(payload)
    assert exc_info.value.code == "WEAK_PASSWORD"


def test_login_user_enumeration_defense(auth_sec_db):
    session, service, active_user, _, _, _ = auth_sec_db

    # Case 1: Unknown user
    with pytest.raises(AegisBaseException) as exc_nonexistent:
        service.login_user("unknown@aegis.enterprise", "SomePassword123!")
    assert exc_nonexistent.value.code == "AUTHENTICATION_FAILED"
    assert exc_nonexistent.value.message == "Invalid credentials provided."

    # Case 2: Wrong password on existing user
    with pytest.raises(AegisBaseException) as exc_wrong_pw:
        service.login_user(active_user.email, "WrongPassword123!")
    assert exc_wrong_pw.value.code == "AUTHENTICATION_FAILED"
    assert exc_wrong_pw.value.message == "Invalid credentials provided."

    # Verify audit logs captured both failure attempts
    failed_logs = session.query(AuditLog).filter(AuditLog.action == "AUTH_LOGIN_FAILED").all()
    assert len(failed_logs) >= 2


def test_login_user_token_claims_and_type(auth_sec_db):
    session, service, active_user, _, _, _ = auth_sec_db
    result = service.login_user(active_user.email, "StrongPass123!")
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"

    # Inspect access token claims
    access_payload = decode_token(result["access_token"], expected_type="access")
    assert access_payload is not None
    assert access_payload["sub"] == str(active_user.id)
    assert access_payload["type"] == "access"
    assert "iss" in access_payload
    assert "aud" in access_payload
    assert "jti" in access_payload
    assert "roles" in access_payload
    assert "permissions" in access_payload

    # Inspect refresh token claims
    refresh_payload = decode_token(result["refresh_token"], expected_type="refresh")
    assert refresh_payload is not None
    assert refresh_payload["sub"] == str(active_user.id)
    assert refresh_payload["type"] == "refresh"


def test_token_type_confusion_defense(auth_sec_db):
    session, service, active_user, _, _, _ = auth_sec_db

    # Create a refresh token
    refresh_token = create_refresh_token(subject=str(active_user.id))

    # Passing refresh token as Bearer token to get_current_user must fail with 401
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=refresh_token, db=session)
    assert exc_info.value.status_code == 401

    # Passing valid access token must succeed
    access_token = create_access_token(
        subject=str(active_user.id),
        roles=["User"],
        permissions=["chat:read"]
    )
    user = get_current_user(token=access_token, db=session)
    assert user.id == active_user.id


def test_token_tampering_and_algorithm_none_rejected():
    token = create_access_token(
        subject="user-uuid",
        roles=["User"],
        permissions=["chat:read"]
    )

    # 1. Signature tampering
    tampered_sig = token[:-6] + "xxxxxx"
    assert decode_token(tampered_sig) is None

    # 2. Algorithm none injection attack
    none_token = jwt.encode(
        {"sub": "user-uuid", "type": "access"},
        key="",
        algorithm="none"
    )
    assert decode_token(none_token) is None


def test_refresh_token_rotation_and_replay_detection(auth_sec_db):
    session, service, active_user, _, _, mock_redis = auth_sec_db

    # Initial login
    login_res = service.login_user(active_user.email, "StrongPass123!")
    initial_refresh = login_res["refresh_token"]

    # 1. Normal rotation (key exists in Redis)
    mock_redis.exists.return_value = 1
    rotated_res = service.rotate_tokens(initial_refresh)
    assert "access_token" in rotated_res
    assert "refresh_token" in rotated_res
    mock_redis.delete.assert_called()

    # 2. Replay attack: session key no longer in Redis (or revoked)
    mock_redis.exists.return_value = 0
    with pytest.raises(AegisBaseException) as exc_info:
        service.rotate_tokens(initial_refresh)
    assert exc_info.value.code == "SECURITY_ALERT"
    mock_redis.keys.assert_called()


def test_account_state_enforcement_and_audit(auth_sec_db):
    session, service, active_user, suspended_user, deleted_user, _ = auth_sec_db

    # Suspended user login fails
    with pytest.raises(AegisBaseException) as exc_suspended:
        service.login_user(suspended_user.email, "StrongPass123!")
    assert exc_suspended.value.code == "ACCOUNT_SUSPENDED"

    # Suspended user token access fails with 403
    suspended_token = create_access_token(
        subject=str(suspended_user.id),
        roles=["User"],
        permissions=["chat:read"]
    )
    with pytest.raises(HTTPException) as exc_403:
        get_current_user(token=suspended_token, db=session)
    assert exc_403.value.status_code == 403

    # Deleted user token access fails with 401
    deleted_token = create_access_token(
        subject=str(deleted_user.id),
        roles=["User"],
        permissions=["chat:read"]
    )
    with pytest.raises(HTTPException) as exc_401:
        get_current_user(token=deleted_token, db=session)
    assert exc_401.value.status_code == 401


def test_user_logout_and_audit(auth_sec_db):
    session, service, active_user, _, _, mock_redis = auth_sec_db
    login_res = service.login_user(active_user.email, "StrongPass123!")
    refresh_tok = login_res["refresh_token"]

    service.logout_user(refresh_tok)
    mock_redis.delete.assert_called()

    logout_log = session.query(AuditLog).filter(
        AuditLog.user_id == active_user.id,
        AuditLog.action == "AUTH_LOGOUT"
    ).first()
    assert logout_log is not None
