from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_current_admin_dependency
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.common import BaseResponse
from app.schemas.document import ReferenceDocumentResponse, PendingReferenceDocumentResponse
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
        
        documents = document_service.get_pending_reference_documents(skip=skip, limit=limit)
        total_count = document_service.get_pending_reference_documents_count()
        
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
        
        approved_document = document_service.approve_pending_reference_document(
            document_id=document_id,
            admin_id=admin_user.id,
            admin_comment=comment
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
        
        rejected_document = document_service.reject_pending_reference_document(
            document_id=document_id,
            admin_id=admin_user.id,
            admin_comment=comment
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


@router.post("/sync-storage", response_model=BaseResponse)
async def synchronize_storage(    
    document_type: str = Query("all", description="Type of documents to synchronize: 'user', 'reference', or 'all'"),
    force_check: bool = Query(False, description="Force check all documents even if they were previously marked as missing"),
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Synchronize MinIO storage with PostgreSQL database records.
    
    This endpoint checks if files in the database exist in MinIO storage.
    If files are missing in MinIO but exist in the database, it marks them as unavailable.
    """
    try:
        document_service = DocumentService(db)
        
        logger.info(f"Starting manual storage synchronization for {document_type} documents")
        
        # Run the synchronization
        results = document_service.synchronize_storage_with_database(document_type=document_type)
        
        if results.get("status") == "failed":
            logger.error("Storage synchronization failed", error=results.get("error"))
            return BaseResponse(
                success=False,
                message=f"Storage synchronization failed: {results.get('error', 'Unknown error')}",
                data=results
            )
        
        # Prepare a more detailed message
        message = f"Storage synchronization completed: {results.get('checked', 0)} documents checked"
        if results.get('missing_in_storage', 0) > 0:
            message += f", {results.get('missing_in_storage', 0)} documents missing in storage"
        
        return BaseResponse(
            success=True,
            message=message,
            data=results
        )
        
    except Exception as e:
        logger.error("Failed to synchronize storage", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synchronize storage: {str(e)}"
        )


@router.delete("/{document_id}", response_model=BaseResponse)
async def delete_reference_document(
    document_id: int,
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Delete a reference document and all related plagiarism matches."""
    try:
        document_service = DocumentService(db)
        
        # Check if document exists
        document = document_service.get_reference_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference document not found"
            )
        
        # Delete the document and related plagiarism matches
        document_service.delete_reference_document(document_id)
        
        return BaseResponse(
            message=f"Reference document {document_id} and all related plagiarism matches deleted successfully"
        )
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to delete reference document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reference document: {str(e)}"
        )
