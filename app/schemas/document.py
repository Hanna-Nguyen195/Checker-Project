from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class UserDocumentBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class UserDocumentCreate(UserDocumentBase):
    pass


class UserDocumentResponse(UserDocumentBase):
    id: int
    user_id: int
    object_id: str
    content_type: Optional[str]
    status: DocumentStatus
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    comment: Optional[str]
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReferenceDocumentBase(BaseModel):
    title: str = Field(..., max_length=255)
    metadata: Optional[Dict[str, Any]] = None


class ReferenceDocumentCreate(ReferenceDocumentBase):
    pass


class ReferenceDocumentResponse(ReferenceDocumentBase):
    id: int
    object_id: str
    content_type: Optional[str]
    created_by: Optional[int]
    source_user_document_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentApprovalRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=500)


class DocumentRejectionRequest(BaseModel):
    comment: str = Field(..., max_length=500, description="Reason for rejection")
