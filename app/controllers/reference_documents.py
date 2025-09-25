from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.common import BaseResponse
from app.utils.validators import validate_file_upload
import structlog

router = APIRouter( tags=["Reference Documents"])
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
        
        if current_user.role == "admin":
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
            # User uploads go to pending reference documents with pending status
            document = document_service.submit_pending_reference_document(
                user_id=current_user.id,
                file_data=file.file,
                filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                title=title or file.filename
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


# Admin-only endpoint moved to admin.py


# Admin-only endpoint moved to admin.py


# Admin-only endpoint moved to admin.py


@router.get("/", response_model=BaseResponse)
async def get_reference_documents(
    skip: int = 0,
    limit: int = 20,
    sync_storage: bool = Query(True, description="Whether to synchronize with MinIO storage"),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get approved reference documents."""
    try:
        document_service = DocumentService(db)
        
        # Optionally synchronize with storage
        sync_results = None
        if sync_storage:
            logger.info("Starting storage synchronization for reference documents")
            sync_results = document_service.synchronize_storage_with_database(document_type="reference")
            logger.info("Storage synchronization completed", 
                      checked=sync_results.get("checked", 0),
                      missing=sync_results.get("missing_in_storage", 0),
                      updated=sync_results.get("updated_records", 0))
        
        documents = document_service.get_reference_documents(skip=skip, limit=limit)
        total_count = document_service.get_reference_documents_count()
        
        response_data = {
            "documents": [
                {
                    "document_id": doc.id,
                    "title": doc.title,
                    "created_by": doc.created_by_user.username if doc.created_by_user else "System",
                    "created_at": doc.created_at,
                    "content_type": doc.content_type,
                    "storage_status": doc.document_metadata.get("storage_status", "unknown") if doc.document_metadata else "unknown"
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
        
        # Include sync results if available
        if sync_results:
            response_data["sync_results"] = sync_results
            
            # Add missing documents information if any
            if sync_results.get("missing_in_storage", 0) > 0 and "missing_documents" in sync_results:
                response_data["missing_documents"] = sync_results["missing_documents"]
        
        # Create a more informative message
        message = "Reference documents retrieved successfully"
        if sync_results:
            message += f" with storage synchronization ({sync_results.get('checked', 0)} checked)"
            if sync_results.get('missing_in_storage', 0) > 0:
                message += f", {sync_results.get('missing_in_storage', 0)} files missing in storage"
        
        return BaseResponse(
            success=True,
            message=message,
            data=response_data
        )
        
    except Exception as e:
        logger.error("Failed to get reference documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reference documents"
        )


# Admin-only endpoint moved to admin.py


# Admin-only endpoint moved to admin.py
