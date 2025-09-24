from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.config.database import Base
from app.models.base import TimestampMixin


class PlagiarismDocument(Base, TimestampMixin):
    """Documents uploaded by users for plagiarism checking"""
    __tablename__ = "plagiarism_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String)
    object_id = Column(String(255), nullable=False)
    content_type = Column(String(100))
    document_metadata = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="plagiarism_documents")
    plagiarism_checks = relationship("PlagiarismCheck", back_populates="plagiarism_document", cascade="all, delete-orphan")


class PendingReferenceDocument(Base, TimestampMixin):
    """Reference documents submitted by users awaiting admin approval"""
    __tablename__ = "pending_reference_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    object_id = Column(String(255), unique=True, nullable=False)
    content_type = Column(String(100))
    status = Column(String(20), default="pending", nullable=False)  # 'pending' | 'approved' | 'rejected'
    admin_comment = Column(String)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    document_metadata = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="pending_reference_documents", foreign_keys=[user_id])
    approved_by_user = relationship("User", back_populates="approved_pending_documents", foreign_keys=[approved_by])
    reference_document = relationship("ReferenceDocument", back_populates="source_pending_document", uselist=False)


class ReferenceDocument(Base, TimestampMixin):
    """Approved reference documents used for plagiarism checking"""
    __tablename__ = "reference_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    object_id = Column(String(255), unique=True, nullable=False)
    content_type = Column(String(100))
    document_metadata = Column(JSON)
    created_by = Column(Integer, ForeignKey("users.id"))
    source_pending_document_id = Column(Integer, ForeignKey("pending_reference_documents.id"))
    
    # Relationships
    created_by_user = relationship("User", back_populates="created_reference_documents")
    source_pending_document = relationship("PendingReferenceDocument", back_populates="reference_document")
    plagiarism_matches = relationship("PlagiarismMatch", back_populates="reference_document")


# Legacy UserDocument model has been removed
