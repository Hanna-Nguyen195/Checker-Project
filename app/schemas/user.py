# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

class Role(str, Enum):
    admin = "admin"
    user = "user"

class Status(str, Enum):
    active = "active"
    inactive = "inactive"

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr
    full_name: str | None = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=6)

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str | None = None
    role: Role
    status: Status

    class Config:
        from_attributes = True
