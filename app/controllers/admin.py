from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import io
import structlog

from app.config.database import get_db
from app.core.dependencies import get_current_admin_dependency, get_pagination_params, PaginationParams
from app.services.admin_service import AdminService
from app.services.document_service import DocumentService
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.document import (
    ReferenceDocumentResponse, 
    DocumentApprovalRequest, 
    DocumentRejectionRequest,
    PendingReferenceDocumentResponse
)
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.validators import validate_file_upload
from app.utils.helpers import create_response_metadata
from app.core.exceptions import NotFoundException

router = APIRouter(tags=["Admin"])
logger = structlog.get_logger(__name__)


@router.get("/stats", response_model=BaseResponse)
async def get_system_statistics(
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get comprehensive system statistics."""
    admin_service = AdminService(db)
    stats = admin_service.get_system_statistics()
    
    return BaseResponse(
        message="System statistics retrieved successfully",
        data=stats
    )


@router.get("/stats/activity", response_model=BaseResponse)
async def get_activity_stats(
    days: int = 30,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get user activity statistics over time."""
    admin_service = AdminService(db)
    activity_stats = admin_service.get_user_activity_stats(days)
    
    return BaseResponse(
        message="Activity statistics retrieved successfully",
        data=activity_stats
    )


@router.get("/stats/similarity-distribution", response_model=BaseResponse)
async def get_similarity_distribution(
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get similarity score distribution."""
    admin_service = AdminService(db)
    distribution = admin_service.get_similarity_distribution()
    
    return BaseResponse(
        message="Similarity distribution retrieved successfully",
        data=distribution
    )


@router.get("/users", response_model=PaginatedResponse)
async def get_all_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get all users with pagination."""
    user_service = UserService(db)
    
    users = user_service.get_users(skip=pagination.offset, limit=pagination.size)
    total_count = user_service.get_users_count()
    
    user_responses = [UserResponse.from_orm(user) for user in users]
    metadata = create_response_metadata(pagination.page, pagination.size, total_count, len(users))
    
    return PaginatedResponse(
        data=user_responses,
        pagination=metadata["pagination"]
    )


@router.put("/users/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Update user information."""
    user_service = UserService(db)
    
    try:
        updated_user = user_service.update_user(user_id, user_data)
        return BaseResponse(
            message="User updated successfully",
            data=UserResponse.from_orm(updated_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/ban", response_model=BaseResponse)
async def ban_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Ban a user."""
    user_service = UserService(db)
    
    try:
        banned_user = user_service.ban_user(user_id)
        return BaseResponse(
            message="User banned successfully",
            data=UserResponse.from_orm(banned_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/unban", response_model=BaseResponse)
async def unban_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Unban a user."""
    user_service = UserService(db)
    
    try:
        unbanned_user = user_service.unban_user(user_id)
        return BaseResponse(
            message="User unbanned successfully",
            data=UserResponse.from_orm(unbanned_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reference-documents/pending", response_model=BaseResponse)
async def get_pending_reference_documents(
    skip: int = 0,
    limit: int = 20,
    current_admin: User = Depends(get_current_admin_dependency),
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


@router.get("/documents/pending/summary", response_model=BaseResponse)
async def get_pending_documents_summary(
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get summary of pending documents."""
    admin_service = AdminService(db)
    summary = admin_service.get_pending_document_summary()
    
    return BaseResponse(
        message="Pending documents summary retrieved successfully",
        data=summary
    )


@router.post("/reference-documents/{document_id}/approve", response_model=BaseResponse)
async def approve_reference_document(
    document_id: int,
    comment: Optional[str] = Form(None),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Approve user document for inclusion in reference database."""
    try:
        document_service = DocumentService(db)
        
        approved_document = document_service.approve_pending_reference_document(
            document_id=document_id,
            admin_id=current_admin.id,
            admin_comment=comment
        )
        
        return BaseResponse(
            success=True,
            message="Document approved and added to reference database",
            data={
                "document_id": approved_document.id,
                "title": approved_document.title,
                "status": approved_document.status,
                "approved_by": current_admin.username,
                "comment": comment
            }
        )
        
    except Exception as e:
        logger.error("Failed to approve document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve document: {str(e)}"
        )


@router.post("/reference-documents/{document_id}/reject", response_model=BaseResponse)
async def reject_reference_document(
    document_id: int,
    comment: str = Form(...),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Reject user document for reference database."""
    try:
        document_service = DocumentService(db)
        
        rejected_document = document_service.reject_pending_reference_document(
            document_id=document_id,
            admin_id=current_admin.id,
            admin_comment=comment
        )
        
        return BaseResponse(
            success=True,
            message="Document rejected",
            data={
                "document_id": rejected_document.id,
                "title": rejected_document.title,
                "status": rejected_document.status,
                "rejected_by": current_admin.username,
                "comment": comment
            }
        )
        
    except Exception as e:
        logger.error("Failed to reject document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject document: {str(e)}"
        )


# Removed redundant create reference document endpoint - using the one in reference_documents.py instead
# which already handles both admin and regular users

@router.get("/reference-documents", response_model=BaseResponse)
async def get_reference_documents(
    pagination: PaginationParams = Depends(get_pagination_params),
    sync_storage: bool = Query(True, description="Whether to synchronize with MinIO storage"),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get reference documents with optional storage synchronization."""
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
        
        documents = document_service.get_reference_documents(
            skip=pagination.offset,
            limit=pagination.size
        )
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
                "skip": pagination.offset,
                "limit": pagination.size,
                "has_more": pagination.offset + pagination.size < total_count
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
        logger.error(f"Error getting reference documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving reference documents"
        )


@router.delete("/reference-documents/{document_id}", response_model=BaseResponse)
async def delete_reference_document(
    document_id: int,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Delete a reference document."""
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


@router.post("/reference-documents/sync-storage", response_model=BaseResponse)
async def synchronize_storage(    
    document_type: str = Query("all", description="Type of documents to synchronize: 'user', 'reference', or 'all'"),
    force_check: bool = Query(False, description="Force check all documents even if they were previously marked as missing"),
    current_admin: User = Depends(get_current_admin_dependency),
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
