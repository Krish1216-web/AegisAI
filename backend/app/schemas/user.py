from pydantic import BaseModel, EmailStr, Field
import uuid
from typing import Optional, Dict, Any

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    role_name: str = Field(default="User")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

class UserSettingsUpdate(BaseModel):
    language: Optional[str] = Field(default="en")
    theme: Optional[str] = Field(default="dark")
    timezone: Optional[str] = Field(default="UTC")
    email_notifications: Optional[bool] = Field(default=True)
    ai_preferences: Optional[Dict[str, Any]] = None

class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    role: RoleResponse
    avatar_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
