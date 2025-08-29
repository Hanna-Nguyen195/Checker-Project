from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.config.database import Base
from app.models.base import TimestampMixin


class ReferenceDocument(Base, TimestampMixin):
    __tablename__ = "reference_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    object_id = Column(String(255), unique=True, nullable=False)
    content_type = Column(String(100))
    document_metadata = Column(JSON)
    created_by = Column(Integer, ForeignKey("users.id"))
    source_user_document_id = Column(Integer)
    
    # Relationships
    created_by_user = relationship("User", back_populates="created_reference_documents")
    plagiarism_matches = relationship("PlagiarismMatch", back_populates="reference_document")


class UserDocument(Base, TimestampMixin):
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String)
    object_id = Column(String(255), nullable=False)
    content_type = Column(String(100))
    status = Column(String(20), default="pending", nullable=False)  # 'pending' | 'approved' | 'rejected'
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    comment = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_documents", foreign_keys=[user_id])
    approved_by_user = relationship("User", back_populates="approved_documents", foreign_keys=[approved_by])
    plagiarism_checks = relationship("PlagiarismCheck", back_populates="user_document", cascade="all, delete-orphan")
