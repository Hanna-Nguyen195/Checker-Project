from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import structlog

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.plagiarism_service import PlagiarismService
from app.schemas.common import BaseResponse
from app.schemas.plagiarism import PlagiarismCheckResponse, ExternalApiResult
from app.schemas.document import PlagiarismDocumentResponse
from app.utils.validators import validate_file_upload

router = APIRouter( tags=["Plagiarism"])
logger = structlog.get_logger(__name__)

# Configuration for external plagiarism API
EXTERNAL_PLAGIARISM_API_URL = "http://your-external-api.com/check-plagiarism"


@router.post("/upload-and-check", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_check_plagiarism(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Upload document to MinIO and create plagiarism check record with processing status.
    The actual plagiarism results will be saved later via save-result API.
    """
    try:
        # Validate file
        validate_file_upload(file)
        
        # Read file content
        file_content = await file.read()
        file.file.seek(0)  # Reset file pointer for document service
        
        # Step 1: Upload and save document to MinIO
        document_service = DocumentService(db)
        document = document_service.upload_plagiarism_document(
            user_id=current_user.id,
            file_data=file.file,
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(file_content),
            title=title
        )
        
        # Step 2: Initiate plagiarism check using the external API
        plagiarism_service = PlagiarismService(db)
        plagiarism_check = plagiarism_service.initiate_external_plagiarism_check(
            document_id=document.id,
            user_id=current_user.id
        )
        
        logger.info(
            "Document uploaded and plagiarism check initiated",
            document_id=document.id,
            check_id=plagiarism_check.id
        )
        
        return BaseResponse(
            success=True,
            message="Document uploaded successfully. Plagiarism check initiated.",
            data={
                "document_id": document.id,
                "check_id": plagiarism_check.id,
                "title": document.title,
                "status": plagiarism_check.check_status,
                "created_at": plagiarism_check.created_at
            }
        )
        
    except Exception as e:
        logger.error("Failed to upload document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post("/save-result/{check_id}", response_model=BaseResponse)
async def save_plagiarism_result(
    check_id: int,
    plagiarism_data: ExternalApiResult,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Save plagiarism check results from external API.
    Updates the plagiarism check record with the results.
    """
    try:
        plagiarism_service = PlagiarismService(db)
        
        # Verify the plagiarism check exists and belongs to the user
        plagiarism_check = plagiarism_service.get_plagiarism_check_by_id(check_id)
        if not plagiarism_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plagiarism check not found"
            )
        
        if plagiarism_check.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this plagiarism check"
            )
        
        # Update plagiarism check with results
        updated_check = plagiarism_service.update_plagiarism_result(
            check_id=check_id,
            external_result=plagiarism_data.dict()
        )
        
        logger.info(
            "Plagiarism check results saved",
            check_id=check_id,
            similarity_score=updated_check.total_similarity_score
        )
        
        return BaseResponse(
            success=True,
            message="Plagiarism check results saved successfully",
            data={
                "check_id": updated_check.id,
                "similarity_score": updated_check.total_similarity_score,
                "status": updated_check.check_status,
                "matches_found": updated_check.matches_found,
                "updated_at": updated_check.updated_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to save plagiarism results", check_id=check_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save plagiarism results"
        )


@router.get("/history", response_model=BaseResponse)
async def get_user_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get user's document upload and plagiarism check history.
    """
    try:
        document_service = DocumentService(db)
        plagiarism_service = PlagiarismService(db)
        
        # Get plagiarism documents with their plagiarism checks
        documents = document_service.get_plagiarism_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        logger.info("Documents retrieved", documents=documents)
        history = []
        for doc in documents:
            # Get plagiarism checks for this document
            checks = plagiarism_service.get_document_plagiarism_checks(doc.id)
            
            doc_data = {
                "document_id": doc.id,
                "title": doc.title,
                # "status": doc.status,
                "uploaded_at": doc.created_at,
                "plagiarism_checks": [
                    {
                        "check_id": check.id,
                        "similarity_score": check.total_similarity_score,
                        "status": check.check_status,
                        "checked_at": check.created_at
                    }
                    for check in checks
                ]
            }
            history.append(doc_data)
        
        # Get total count for pagination
        total_count = document_service.get_plagiarism_documents_count(current_user.id)
        
        return BaseResponse(
            success=True,
            message="User history retrieved successfully",
            data={
                "history": history,
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                }
            }
        )
        
    except Exception as e:
        logger.error("Failed to get user history", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user history"
        )


@router.post("/check-by-document-id/{document_id}", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def check_plagiarism_by_document_id(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Start a plagiarism check for an existing document using its ID.
    Returns a plagiarism check record with processing status.
    """
    try:
        
        # Verify the document exists and belongs to the user
        document_service = DocumentService(db)
        document = document_service.get_plagiarism_document(document_id, current_user.id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or you don't have access to it"
            )
        
        # Initiate plagiarism check using the external API
        plagiarism_service = PlagiarismService(db)
        updated_check = plagiarism_service.initiate_external_plagiarism_check(
            document_id=document.id,
            user_id=current_user.id
        )
        
        logger.info(
            "Plagiarism check initiated for existing document",
            document_id=document.id,
            check_id=updated_check.id
        )
        
        return BaseResponse(
            success=True,
            message="Plagiarism check initiated successfully.",
            data={
                "document_id": document.id,
                "check_id": updated_check.id,
                "title": document.title,
                "status": updated_check.check_status,
                "created_at": updated_check.created_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to initiate plagiarism check", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate plagiarism check: {str(e)}"
        )
