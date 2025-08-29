from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io
import structlog
from urllib.parse import quote

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_pagination_params, PaginationParams
from app.core.exceptions import NotFoundException, StorageException, ValidationException, FileUploadException
from app.services.document_service import DocumentService
from app.models.user import User
from app.schemas.document import UserDocumentResponse, UserDocumentCreate
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.validators import validate_file_upload
from app.utils.helpers import create_response_metadata

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/upload", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Upload a document for plagiarism checking."""
    try:
        # Validate file first (before any database operations)
        validate_file_upload(file)
        
        # Read file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        
        # Create document service
        document_service = DocumentService(db)
        
        document = document_service.upload_user_document(
            user_id=current_user.id,
            file_data=file_stream,
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(file_content),
            title=title
        )
        
        return BaseResponse(
            message="Document uploaded successfully",
            data=UserDocumentResponse.from_orm(document)
        )
    except FileUploadException as e:
        logger.warning("File upload validation failed", error=str(e), filename=file.filename)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationException as e:
        logger.warning("File validation failed", error=str(e), filename=file.filename)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except StorageException as e:
        logger.error("Storage service error", error=str(e), filename=file.filename)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Storage service unavailable: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error in upload_document", error=str(e), filename=file.filename, user_id=current_user.id)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("", response_model=PaginatedResponse)
async def get_user_documents(
    status_filter: Optional[str] = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's documents with pagination."""
    document_service = DocumentService(db)
    
    documents = document_service.get_user_documents(
        user_id=current_user.id,
        status=status_filter,
        skip=pagination.offset,
        limit=pagination.size
    )
    
    total_count = document_service.get_user_documents_count(
        user_id=current_user.id,
        status=status_filter
    )
    
    document_responses = [UserDocumentResponse.from_orm(doc) for doc in documents]
    metadata = create_response_metadata(pagination.page, pagination.size, total_count, len(documents))
    
    return PaginatedResponse(
        data=document_responses,
        pagination=metadata["pagination"]
    )


@router.get("/{document_id}", response_model=BaseResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get document details."""
    document_service = DocumentService(db)
    
    document = document_service.get_user_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    return BaseResponse(
        data=UserDocumentResponse.from_orm(document)
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Download document file."""
    document_service = DocumentService(db)
    
    try:
        # Check if document exists first
        document = document_service.get_user_document(document_id, current_user.id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        # Download the file content
        file_content = document_service.download_user_document(document_id, current_user.id)
        
        # Properly encode filename for Content-Disposition header
        encoded_filename = quote(document.title.encode('utf-8'))
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=document.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error in download_document", error=str(e), document_id=document_id, user_id=current_user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{document_id}", response_model=BaseResponse)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete document."""
    document_service = DocumentService(db)
    
    try:
        document_service.delete_user_document(document_id, current_user.id)
        return BaseResponse(message="Document deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
