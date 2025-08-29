from sqlalchemy import Column, Integer, String, Date, Boolean, Numeric, Index, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from decimal import Decimal

from app.config.database import Base
from app.models.base import TimestampMixin


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    check_limit = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user_plans = relationship("UserPlan", back_populates="plan")


class UserPlan(Base, TimestampMixin):
    __tablename__ = "user_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    checks_used = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_plans")
    plan = relationship("Plan", back_populates="user_plans")
    
    __table_args__ = (
        Index('idx_user_active_plan', 'user_id', 'is_active', 'end_date'),
    )


class SystemStats(Base, TimestampMixin):
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, unique=True)
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    total_user_documents = Column(Integer, default=0)
    total_reference_documents = Column(Integer, default=0)
    total_checks = Column(Integer, default=0)
    average_similarity = Column(Numeric(5, 2), default=0)
