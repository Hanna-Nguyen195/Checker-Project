from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.utils.validators import validate_password, validate_username


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    BANNED = "banned"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE

    @validator('username')
    def validate_username_format(cls, v):
        if not validate_username(v):
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @validator('password')
    def validate_password_strength(cls, v):
        if not validate_password(v):
            raise ValueError(
                'Password must contain at least 8 characters with uppercase, lowercase, digit, and special character'
            )
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str


class UserPasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_password_strength(cls, v):
        if not validate_password(v):
            raise ValueError(
                'Password must contain at least 8 characters with uppercase, lowercase, digit, and special character'
            )
        return v


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_password_strength(cls, v):
        if not validate_password(v):
            raise ValueError(
                'Password must contain at least 8 characters with uppercase, lowercase, digit, and special character'
            )
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
