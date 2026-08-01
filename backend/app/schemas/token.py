from pydantic import BaseModel
from typing import List, Optional
import uuid

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str
    exp: int
    jti: str
    roles: List[str]
    permissions: List[str]

class RefreshTokenPayload(BaseModel):
    sub: str
    exp: int
    jti: str
