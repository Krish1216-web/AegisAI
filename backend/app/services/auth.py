from sqlalchemy.orm import Session
import redis
from loguru import logger
import uuid
from datetime import timedelta

from app.repositories.user import UserRepository, RoleRepository
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
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

    def register_user(self, payload: UserCreate) -> User:
        """
        Creates a new user, hashes their password, and assigns the target role.
        """
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
        
        return created_user

    def login_user(self, username_or_email: str, plain_password: str) -> dict:
        """
        Verifies credentials, registers session keys, and returns token pairs.
        """
        # Query user by username or email
        user = self.user_repo.get_by_email(username_or_email)
        if not user:
            user = self.user_repo.get_by_username(username_or_email)
            
        if not user or not verify_password(plain_password, user.password_hash):
            raise AegisBaseException("Invalid credentials provided.", code="AUTHENTICATION_FAILED")
            
        if not user.is_active:
            raise AegisBaseException("This user account has been suspended.", code="ACCOUNT_SUSPENDED")

        # Set user permissions lists based on role
        permissions = ["chat:read", "chat:write"]
        if user.role.name in ["Admin", "Super Admin"]:
            permissions.extend(["mcp:configure", "user:provision"])
        if user.role.name == "Super Admin":
            permissions.append("system:bypass")

        # Create token pairs
        access_token = create_access_token(
            subject=str(user.id),
            roles=[user.role.name],
            permissions=permissions
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        # Register refresh token JTI in Redis session cache
        payload = decode_token(refresh_token)
        if payload:
            jti = payload.get("jti")
            session_key = f"aegis:session:{user.id}:{jti}"
            self.redis.hset(session_key, mapping={
                "status": "active",
                "jti": jti
            })
            self.redis.expire(session_key, timedelta(days=7))

        logger.info(f"User login successful: {user.username} (Role: {user.role.name})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def rotate_tokens(self, refresh_token: str) -> dict:
        """
        Processes token rotation, verifying refresh tokens, and issuing new token pairs.
        """
        payload = decode_token(refresh_token)
        if not payload:
            raise AegisBaseException("Invalid refresh token.", code="TOKEN_ROTATION_FAILED")

        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Check if this token was already revoked or is not active in Redis
        session_key = f"aegis:session:{user_id}:{jti}"
        if not self.redis.exists(session_key):
            # Potential replay attack! Revoke all user sessions for safety.
            logger.warning(f"Replay attack detected for user ID: {user_id}. Revoking all sessions!")
            self.revoke_all_sessions(user_id)
            raise AegisBaseException("Refresh token was already used. Session terminated.", code="SECURITY_ALERT")

        # Retrieve user
        user = self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise AegisBaseException("User account is inactive or not found.", code="TOKEN_ROTATION_FAILED")

        # Mark old token as revoked in Redis
        self.redis.delete(session_key)

        # Generate new token pairs
        permissions = ["chat:read", "chat:write"]
        if user.role.name in ["Admin", "Super Admin"]:
            permissions.extend(["mcp:configure", "user:provision"])
        if user.role.name == "Super Admin":
            permissions.append("system:bypass")

        new_access = create_access_token(
            subject=str(user.id),
            roles=[user.role.name],
            permissions=permissions
        )
        new_refresh = create_refresh_token(subject=str(user.id))

        # Register new JTI in Redis
        new_payload = decode_token(new_refresh)
        if new_payload:
            new_jti = new_payload.get("jti")
            new_session_key = f"aegis:session:{user.id}:{new_jti}"
            self.redis.hset(new_session_key, mapping={
                "status": "active",
                "jti": new_jti
            })
            self.redis.expire(new_session_key, timedelta(days=7))

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }

    def logout_user(self, refresh_token: str):
        """
        Clears the session validation keys in Redis.
        """
        payload = decode_token(refresh_token)
        if payload:
            user_id = payload.get("sub")
            jti = payload.get("jti")
            session_key = f"aegis:session:{user_id}:{jti}"
            self.redis.delete(session_key)
            logger.info(f"User logout complete for session: {jti}")

    def revoke_all_sessions(self, user_id: str):
        """
        Revokes all active sessions for a user ID.
        """
        pattern = f"aegis:session:{user_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
            logger.info(f"Revoked {len(keys)} active sessions for user: {user_id}")
