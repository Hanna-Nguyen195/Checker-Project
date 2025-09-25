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


# Moved to admin.py since getting reference documents should be admin-only

# Admin-only endpoint moved to admin.py


# Admin-only endpoint moved to admin.py
