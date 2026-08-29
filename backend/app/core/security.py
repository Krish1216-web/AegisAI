from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional
import jwt
from jwt.exceptions import PyJWTError as JWTError
from passlib.context import CryptContext
from loguru import logger
import uuid

from app.core.config import settings

import bcrypt
# Initialize password hash context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if a plain text password matches the saved hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
    except Exception:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

def get_password_hash(password: str) -> str:
    """
    Computes a secure bcrypt hash of a plain text password.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8')[:72], salt).decode('utf-8')

def create_access_token(
    subject: str,
    roles: List[str],
    permissions: List[str],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generates a short-lived access JWT token with RBAC claims.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "iss": "https://aegisai.enterprise",
        "sub": str(subject),
        "aud": "https://api.aegisai.enterprise",
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": f"jwt_access_{uuid.uuid4()}",
        "roles": roles,
        "permissions": permissions
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a long-lived refresh token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode = {
        "iss": "https://aegisai.enterprise",
        "sub": str(subject),
        "aud": "https://api.aegisai.enterprise",
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": f"jwt_refresh_{uuid.uuid4()}"
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decrypts and validates the JWT signature and expiration.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience="https://api.aegisai.enterprise"
        )
        return payload
    except JWTError:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_aud": False}
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT signature verification failed: {e}")
            return None
