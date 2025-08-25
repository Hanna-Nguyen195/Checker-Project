from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_current_admin_dependency
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.common import BaseResponse
from app.schemas.document import UserDocumentResponse, ReferenceDocumentResponse
from app.utils.validators import validate_file_upload
import structlog

router = APIRouter(prefix="/reference-documents", tags=["Reference Documents"])
logger = structlog.get_logger(__name__)


@router.post("/upload", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_reference_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Upload reference document. 
    - Users: Creates pending document requiring admin approval
    - Admins: Creates approved reference document immediately
    """
    try:
        validate_file_upload(file)
        
        file_content = await file.read()
        file.file.seek(0)
        
        document_service = DocumentService(db)
        
        if current_user.is_admin:
            # Admin uploads go directly to reference documents
            document = document_service.create_reference_document(
                admin_id=current_user.id,
                file_data=file.file,
                filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                title=title
            )
            
            return BaseResponse(
                success=True,
                message="Reference document created successfully",
                data={
                    "document_id": document.id,
                    "title": document.title,
                    "status": "approved",
                    "type": "reference"
                }
            )
        else:
            # User uploads go to user documents with pending status
            document = document_service.upload_user_document(
                user_id=current_user.id,
                file_data=file.file,
                filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                title=title
            )
            
            return BaseResponse(
                success=True,
                message="Document uploaded successfully. Awaiting admin approval to become reference document.",
                data={
                    "document_id": document.id,
                    "title": document.title,
                    "status": "pending",
                    "type": "user_submission"
                }
            )
            
    except Exception as e:
        logger.error("Failed to upload reference document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/pending", response_model=BaseResponse)
async def get_pending_reference_documents(
    skip: int = 0,
    limit: int = 20,
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get pending user documents awaiting approval for reference database."""
    try:
        document_service = DocumentService(db)
        
        documents = document_service.get_pending_documents(skip=skip, limit=limit)
        total_count = document_service.get_pending_documents_count()
        
        return BaseResponse(
            success=True,
            message="Pending documents retrieved successfully",
            data={
                "documents": [
                    {
                        "document_id": doc.id,
                        "title": doc.title,
                        "uploaded_by": doc.user.username,
                        "uploaded_at": doc.created_at,
                        "content_type": doc.content_type,
                        "status": doc.status
                    }
                    for doc in documents
                ],
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                }
            }
        )
        
    except Exception as e:
        logger.error("Failed to get pending documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pending documents"
        )


@router.post("/{document_id}/approve", response_model=BaseResponse)
async def approve_reference_document(
    document_id: int,
    comment: Optional[str] = Form(None),
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Approve user document for inclusion in reference database."""
    try:
        document_service = DocumentService(db)
        
        approved_document = document_service.approve_user_document(
            document_id=document_id,
            admin_id=admin_user.id,
            comment=comment
        )
        
        return BaseResponse(
            success=True,
            message="Document approved and added to reference database",
            data={
                "document_id": approved_document.id,
                "title": approved_document.title,
                "status": approved_document.status,
                "approved_by": admin_user.username,
                "comment": comment
            }
        )
        
    except Exception as e:
        logger.error("Failed to approve document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve document: {str(e)}"
        )


@router.post("/{document_id}/reject", response_model=BaseResponse)
async def reject_reference_document(
    document_id: int,
    comment: str = Form(...),
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Reject user document for reference database."""
    try:
        document_service = DocumentService(db)
        
        rejected_document = document_service.reject_user_document(
            document_id=document_id,
            admin_id=admin_user.id,
            comment=comment
        )
        
        return BaseResponse(
            success=True,
            message="Document rejected",
            data={
                "document_id": rejected_document.id,
                "title": rejected_document.title,
                "status": rejected_document.status,
                "rejected_by": admin_user.username,
                "comment": comment
            }
        )
        
    except Exception as e:
        logger.error("Failed to reject document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject document: {str(e)}"
        )


@router.get("/", response_model=BaseResponse)
async def get_reference_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get approved reference documents."""
    try:
        document_service = DocumentService(db)
        
        documents = document_service.get_reference_documents(skip=skip, limit=limit)
        total_count = document_service.get_reference_documents_count()
        
        return BaseResponse(
            success=True,
            message="Reference documents retrieved successfully",
            data={
                "documents": [
                    {
                        "document_id": doc.id,
                        "title": doc.title,
                        "created_by": doc.creator.username if doc.creator else "System",
                        "created_at": doc.created_at,
                        "content_type": doc.content_type
                    }
                    for doc in documents
                ],
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                }
            }
        )
        
    except Exception as e:
        logger.error("Failed to get reference documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reference documents"
        )
