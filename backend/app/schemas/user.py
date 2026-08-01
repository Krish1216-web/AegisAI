from pydantic import BaseModel, EmailStr, Field
import uuid
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    role_name: str = Field(default="User") # Default to normal user role

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

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

    class Config:
        from_attributes = True
