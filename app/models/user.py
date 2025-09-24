from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.config.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="user", nullable=False)  # 'user' | 'admin'
    status = Column(String(20), default="active", nullable=False)  # 'active' | 'banned'
    reset_token = Column(String(255))
    reset_token_expiry = Column(DateTime)
    
    # New relationships for three-database structure
    plagiarism_documents = relationship("PlagiarismDocument", back_populates="user", cascade="all, delete-orphan")
    pending_reference_documents = relationship("PendingReferenceDocument", back_populates="user", foreign_keys="PendingReferenceDocument.user_id", cascade="all, delete-orphan")
    created_reference_documents = relationship("ReferenceDocument", back_populates="created_by_user")
    approved_pending_documents = relationship("PendingReferenceDocument", foreign_keys="PendingReferenceDocument.approved_by", back_populates="approved_by_user")
    
    # Other relationships
    plagiarism_checks = relationship("PlagiarismCheck", back_populates="user")
    user_plans = relationship("UserPlan", back_populates="user", cascade="all, delete-orphan")
    
    # Legacy relationships have been removed
    