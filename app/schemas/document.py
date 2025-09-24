from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# PlagiarismDocument schemas
class PlagiarismDocumentBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class PlagiarismDocumentCreate(PlagiarismDocumentBase):
    pass


class PlagiarismDocumentResponse(PlagiarismDocumentBase):
    id: int
    user_id: int
    object_id: str
    content_type: Optional[str]
    document_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# PendingReferenceDocument schemas
class PendingReferenceDocumentBase(BaseModel):
    title: str = Field(..., max_length=255)


class PendingReferenceDocumentCreate(PendingReferenceDocumentBase):
    pass


class PendingReferenceDocumentResponse(PendingReferenceDocumentBase):
    id: int
    user_id: int
    object_id: str
    content_type: Optional[str]
    status: DocumentStatus
    admin_comment: Optional[str]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    document_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ReferenceDocument schemas
class ReferenceDocumentBase(BaseModel):
    title: str = Field(..., max_length=255)
    document_metadata: Optional[Dict[str, Any]] = None


class ReferenceDocumentCreate(ReferenceDocumentBase):
    pass


class ReferenceDocumentResponse(ReferenceDocumentBase):
    id: int
    object_id: str
    content_type: Optional[str]
    created_by: Optional[int]
    source_pending_document_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Legacy schemas have been removed


class DocumentApprovalRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=500)


class DocumentRejectionRequest(BaseModel):
    comment: str = Field(..., max_length=500, description="Reason for rejection")
