import enum
from datetime import datetime
from sqlalchemy import String, Integer, Text, Enum, TIMESTAMP, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"

class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.active, nullable=False)

    reset_token: Mapped[str | None] = mapped_column(String(255))
    reset_token_expiry: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

Index("ix_users_username_email", User.username, User.email)
