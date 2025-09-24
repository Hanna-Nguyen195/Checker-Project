from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.config.database import Base
from app.models.base import TimestampMixin


class PlagiarismCheck(Base, TimestampMixin):
    __tablename__ = "plagiarism_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plagiarism_document_id = Column(Integer, ForeignKey("plagiarism_documents.id"), nullable=False)
    total_similarity_score = Column(Float, nullable=False)
    check_status = Column(String(20), default="completed", nullable=False)  # 'processing' | 'completed' | 'failed'
    processing_time = Column(Integer)  # Time in milliseconds
    reference_documents_count = Column(Integer, default=0)
    matches_found = Column(Integer, default=0)
    check_metadata = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="plagiarism_checks")
    plagiarism_document = relationship("PlagiarismDocument", back_populates="plagiarism_checks")
    plagiarism_matches = relationship("PlagiarismMatch", back_populates="check", cascade="all, delete-orphan")
    
    # Legacy relationship has been removed
    
    __table_args__ = (
        Index('idx_user_checks', 'user_id', 'created_at'),
    )


class PlagiarismMatch(Base, TimestampMixin):
    __tablename__ = "plagiarism_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(Integer, ForeignKey("plagiarism_checks.id"), nullable=False)
    reference_document_id = Column(Integer, ForeignKey("reference_documents.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    matched_sentences_count = Column(Integer, default=0)
    match_metadata = Column(JSON)
    
    # Relationships
    check = relationship("PlagiarismCheck", back_populates="plagiarism_matches")
    reference_document = relationship("ReferenceDocument", back_populates="plagiarism_matches")
    sentence_matches = relationship("SentenceMatch", back_populates="match", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_check_reference', 'check_id', 'reference_document_id'),
        Index('idx_similarity_score', 'similarity_score'),
    )


class SentenceMatch(Base, TimestampMixin):
    __tablename__ = "sentence_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("plagiarism_matches.id"), nullable=False)
    user_sentence_text = Column(String, nullable=False)
    user_sentence_start = Column(Integer, nullable=False)
    user_sentence_end = Column(Integer, nullable=False)
    reference_sentence_text = Column(String, nullable=False)
    reference_sentence_start = Column(Integer, nullable=False)
    reference_sentence_end = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    match_type = Column(String(20), default="exact", nullable=False)  # 'exact' | 'paraphrase' | 'partial' | 'detected'
    page_number = Column(Integer, default=1)  # Page number where match was found
    bounding_boxes = Column(JSON)  # Store bounding box coordinates as JSON
    
    # Relationships
    match = relationship("PlagiarismMatch", back_populates="sentence_matches")
    
    __table_args__ = (
        Index('idx_match_sentences', 'match_id'),
    )
