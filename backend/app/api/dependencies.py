from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Generator
import uuid

from app.database.session import get_db
from app.repositories.user import UserRepository
from app.models.user import User
from app.core.security import decode_token

# Configure OAuth2PasswordBearer to resolve token headers
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency provider extracting the authenticated user from the request header JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
        
    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception
        
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(uuid.UUID(user_id))
    if not user:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended"
        )
        
    return user

class RoleChecker:
    """
    Dependency checker validating if the current user possesses authorized roles.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.name
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires roles: {self.allowed_roles}. Current role: {user_role}"
            )
        return current_user

from app.models.workspace import WorkspaceMember

def get_workspace_member(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WorkspaceMember:
    """
    Dependency checking that the authenticated user is a valid member of the target workspace.
    """
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access permissions for this workspace."
        )
    return member

import time
from app.database.redis import get_redis
from app.core.config import settings
from typing import Any

def check_rate_limit(
    current_user: User = Depends(get_current_user),
    redis_client: Any = Depends(get_redis)
) -> None:
    user_id = str(current_user.id)
    minute_timestamp = int(time.time() // 60)
    key = f"aegis:ratelimit:{user_id}:{minute_timestamp}"
    
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 60)
        
        limit = settings.RATE_LIMIT_RPM
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a minute."
            )
    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis rate limiting error: {e}")

