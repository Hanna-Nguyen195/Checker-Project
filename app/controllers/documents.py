from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import structlog
from urllib.parse import quote

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency
from app.core.exceptions import NotFoundException, StorageException
from app.services.document_service import DocumentService
from app.models.user import User
from app.schemas.document import PlagiarismDocumentResponse
from app.schemas.common import BaseResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


# Removed POST /documents/upload endpoint - using /plagiarism/upload-and-check instead

# Removed GET /documents endpoint - using /plagiarism/history instead

@router.get("/{document_id}", response_model=BaseResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get document details."""
    document_service = DocumentService(db)
    
    document = document_service.get_plagiarism_document(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    return BaseResponse(
        data=PlagiarismDocumentResponse.from_orm(document)
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
        document = document_service.get_plagiarism_document(document_id, current_user.id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        # Download the file content
        file_content = document_service.download_plagiarism_document(document_id, current_user.id)
        
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
        document_service.delete_plagiarism_document(document_id, current_user.id)
        return BaseResponse(message="Document deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
