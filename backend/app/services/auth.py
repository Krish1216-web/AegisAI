from sqlalchemy.orm import Session
import redis
from loguru import logger
import uuid
from datetime import timedelta

from app.repositories.user import UserRepository, RoleRepository
from app.models.user import User
from app.models.audit import AuditLog
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength,
)
from app.core.exceptions import AegisBaseException, EntityNotFoundError
from app.schemas.user import UserCreate

class AuthService:
    """
    Service layer coordinates registration, logins, session caching, and token rotations.
    """
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def _record_audit(
        self,
        user_id: uuid.UUID | None,
        action: str,
        details: str | None = None,
        ip_address: str | None = None
    ) -> None:
        try:
            audit = AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                details=details
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            logger.debug(f"Audit log recording skipped or failed: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    def register_user(self, payload: UserCreate) -> User:
        """
        Creates a new user, hashes their password, and assigns the target role.
        """
        # Validate password strength
        is_valid, reason = validate_password_strength(payload.password)
        if not is_valid:
            raise AegisBaseException(reason, code="WEAK_PASSWORD")

        # Check if email already registered
        if self.user_repo.get_by_email(payload.email):
            raise AegisBaseException("This email is already registered.", code="REGISTRATION_FAILED")
        
        # Check if username already taken
        if self.user_repo.get_by_username(payload.username):
            raise AegisBaseException("This username is already taken.", code="REGISTRATION_FAILED")

        # Resolve or seed target Role
        role = self.role_repo.get_by_name(payload.role_name)
        if not role:
            # Auto-seed role if it doesn't exist
            role = self.role_repo.create(name=payload.role_name, description=f"{payload.role_name} system role.")

        hashed_password = get_password_hash(payload.password)
        
        # Create default organization & workspace
        org_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        
        from app.models.workspace import Organization, Workspace, WorkspaceMember
        default_org = Organization(
            id=org_id,
            name=f"{payload.username}'s Organization"
        )
        self.db.add(default_org)
        
        default_workspace = Workspace(
            id=workspace_id,
            organization_id=org_id,
            name=f"{payload.username}'s Workspace"
        )
        self.db.add(default_workspace)

        new_user = User(
            email=payload.email,
            username=payload.username,
            password_hash=hashed_password,
            role_id=role.id,
            is_active=True,
            is_verified=False,
            settings={"default_workspace_id": str(workspace_id)}
        )
        created_user = self.user_repo.create(new_user)
        
        # Add creator as Workspace Owner
        member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            user_id=created_user.id,
            role="owner"
        )
        self.db.add(member)
        self.db.commit()
        
        self._record_audit(
            user_id=created_user.id,
            action="AUTH_REGISTER",
            details=f"User registered: {created_user.username} ({created_user.email})"
        )

        return created_user

    def login_user(self, username_or_email: str, plain_password: str, ip_address: str | None = None) -> dict:
        """
        Verifies credentials, registers session keys, and returns token pairs.
        Resistant to account enumeration by returning uniform error messages.
        """
        user = self.user_repo.get_by_email(username_or_email)
        if not user:
            user = self.user_repo.get_by_username(username_or_email)
            
        if not user or not verify_password(plain_password, user.password_hash):
            self._record_audit(
                user_id=user.id if user else None,
                action="AUTH_LOGIN_FAILED",
                details=f"Failed login attempt for identifier: {username_or_email}",
                ip_address=ip_address
            )
            raise AegisBaseException("Invalid credentials provided.", code="AUTHENTICATION_FAILED")
            
        if not user.is_active:
            self._record_audit(
                user_id=user.id,
                action="AUTH_LOGIN_FAILED",
                details=f"Suspended account login attempt: {user.username}",
                ip_address=ip_address
            )
            raise AegisBaseException("This user account has been suspended.", code="ACCOUNT_SUSPENDED")

        # Set user permissions lists based on role
        permissions = ["chat:read", "chat:write"]
        if user.role and user.role.name in ["Admin", "Super Admin"]:
            permissions.extend(["mcp:configure", "user:provision"])
        if user.role and user.role.name == "Super Admin":
            permissions.append("system:bypass")

        role_name = user.role.name if user.role else "User"

        # Create token pairs
        access_token = create_access_token(
            subject=str(user.id),
            roles=[role_name],
            permissions=permissions
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        # Register refresh token JTI in Redis session cache
        payload = decode_token(refresh_token, expected_type="refresh")
        if payload and self.redis:
            try:
                jti = payload.get("jti")
                session_key = f"aegis:session:{user.id}:{jti}"
                self.redis.hset(session_key, mapping={
                    "status": "active",
                    "jti": str(jti)
                })
                self.redis.expire(session_key, timedelta(days=7))
            except Exception as re:
                logger.warning(f"Redis session cache unavailable: {re}")

        self._record_audit(
            user_id=user.id,
            action="AUTH_LOGIN_SUCCESS",
            details=f"User logged in: {user.username} (Role: {role_name})",
            ip_address=ip_address
        )

        logger.info(f"User login successful: {user.username} (Role: {role_name})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def rotate_tokens(self, refresh_token: str) -> dict:
        """
        Processes token rotation, verifying refresh tokens, checking replay, and issuing new token pairs.
        """
        payload = decode_token(refresh_token, expected_type="refresh")
        if not payload:
            raise AegisBaseException("Invalid refresh token.", code="TOKEN_ROTATION_FAILED")

        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Check if this token was already revoked or is not active in Redis
        session_key = f"aegis:session:{user_id}:{jti}"
        if self.redis:
            try:
                exists = self.redis.exists(session_key)
                if exists is False or exists == 0:
                    # Potential replay attack! Revoke all user sessions for safety.
                    logger.warning(f"Replay attack detected for user ID: {user_id}. Revoking all sessions!")
                    self.revoke_all_sessions(user_id)
                    self._record_audit(
                        user_id=uuid.UUID(user_id) if user_id else None,
                        action="AUTH_REPLAY_ATTACK_DETECTED",
                        details=f"Replay attack detected on session key: {session_key}"
                    )
                    raise AegisBaseException("Refresh token was already used. Session terminated.", code="SECURITY_ALERT")
            except AegisBaseException:
                raise
            except Exception as re:
                logger.warning(f"Redis session check warning during rotation: {re}")

        # Retrieve user
        try:
            user_uuid = uuid.UUID(user_id)
        except Exception:
            raise AegisBaseException("Invalid token subject.", code="TOKEN_ROTATION_FAILED")

        user = self.user_repo.get_by_id(user_uuid)
        if not user or not user.is_active:
            raise AegisBaseException("User account is inactive or not found.", code="TOKEN_ROTATION_FAILED")

        # Mark old token as revoked in Redis
        if self.redis:
            try:
                self.redis.delete(session_key)
            except Exception as e:
                logger.warning(f"Redis session delete failed: {e}")

        # Generate new token pairs
        permissions = ["chat:read", "chat:write"]
        role_name = user.role.name if user.role else "User"
        if user.role and user.role.name in ["Admin", "Super Admin"]:
            permissions.extend(["mcp:configure", "user:provision"])
        if user.role and user.role.name == "Super Admin":
            permissions.append("system:bypass")

        new_access = create_access_token(
            subject=str(user.id),
            roles=[role_name],
            permissions=permissions
        )
        new_refresh = create_refresh_token(subject=str(user.id))

        # Register new JTI in Redis
        new_payload = decode_token(new_refresh, expected_type="refresh")
        if new_payload and self.redis:
            try:
                new_jti = new_payload.get("jti")
                new_session_key = f"aegis:session:{user.id}:{new_jti}"
                self.redis.hset(new_session_key, mapping={
                    "status": "active",
                    "jti": str(new_jti)
                })
                self.redis.expire(new_session_key, timedelta(days=7))
            except Exception as re:
                logger.warning(f"Redis session registration warning: {re}")

        self._record_audit(
            user_id=user.id,
            action="AUTH_TOKEN_ROTATED",
            details=f"Token rotated for user: {user.username}"
        )

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }

    def logout_user(self, refresh_token: str):
        """
        Clears the session validation keys in Redis and records audit.
        """
        payload = decode_token(refresh_token, expected_type="refresh")
        if payload:
            user_id = payload.get("sub")
            jti = payload.get("jti")
            session_key = f"aegis:session:{user_id}:{jti}"
            if self.redis:
                try:
                    self.redis.delete(session_key)
                except Exception as e:
                    logger.warning(f"Redis session delete failed during logout: {e}")
            self._record_audit(
                user_id=uuid.UUID(user_id) if user_id else None,
                action="AUTH_LOGOUT",
                details=f"User logout complete for session: {jti}"
            )
            logger.info(f"User logout complete for session: {jti}")

    def revoke_all_sessions(self, user_id: str):
        """
        Revokes all active sessions for a user ID.
        """
        if not self.redis:
            return
        try:
            pattern = f"aegis:session:{user_id}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info(f"Revoked {len(keys)} active sessions for user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to revoke all sessions in Redis: {e}")
