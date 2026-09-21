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

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforces enterprise password strength policies.
    - Length between 8 and 128 characters
    - Must contain at least one letter and at least one digit or special character
    - Reject empty/pure whitespace
    """
    if not password or not password.strip():
        return False, "Password cannot be empty or whitespace only."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    
    has_letter = any(c.isalpha() for c in password)
    has_digit_or_special = any(c.isdigit() or not c.isalnum() for c in password)
    
    if not (has_letter and has_digit_or_special):
        return False, "Password must contain a mix of letters and numbers/special characters."
        
    return True, "Password meets security requirements."

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
        "type": "access",
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
        "jti": f"jwt_refresh_{uuid.uuid4()}",
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Decrypts and validates the JWT signature, algorithm, expiration, and optional token type.
    Explicitly rejects 'none' algorithm and unapproved algorithms.
    """
    if not token or not isinstance(token, str):
        return None
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        if not alg or alg.lower() == "none" or alg != settings.ALGORITHM:
            logger.warning(f"JWT rejected due to invalid or unapproved algorithm: {alg}")
            return None
    except Exception as e:
        logger.warning(f"JWT header extraction failed: {e}")
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience="https://api.aegisai.enterprise"
        )
    except JWTError:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_aud": False}
            )
        except JWTError as e:
            logger.warning(f"JWT signature verification failed: {e}")
            return None

    if expected_type is not None:
        token_type = payload.get("type")
        if token_type is not None and token_type != expected_type:
            logger.warning(f"JWT token type mismatch: expected {expected_type}, got {token_type}")
            return None

    return payload
