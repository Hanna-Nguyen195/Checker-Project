from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import io

from app.config.database import get_db
from app.core.dependencies import get_current_admin_dependency, get_pagination_params, PaginationParams
from app.services.admin_service import AdminService
from app.services.document_service import DocumentService
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.document import (
    ReferenceDocumentResponse, 
    DocumentApprovalRequest, 
    DocumentRejectionRequest
)
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.validators import validate_file_upload
from app.utils.helpers import create_response_metadata

router = APIRouter()


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


# Legacy endpoint for pending documents has been removed


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


# Legacy endpoint for approving user documents has been removed


# Legacy endpoint for rejecting user documents has been removed


@router.post("/reference-documents", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_reference_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Create a reference document directly."""
    validate_file_upload(file)
    
    document_service = DocumentService(db)
    
    try:
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        
        document = document_service.create_reference_document(
            admin_id=current_admin.id,
            file_data=file_stream,
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(file_content),
            title=title
        )
        
        return BaseResponse(
            message="Reference document created successfully",
            data=ReferenceDocumentResponse.from_orm(document)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reference-documents", response_model=PaginatedResponse)
async def get_reference_documents(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get reference documents."""
    try:
        document_service = DocumentService(db)
        
        documents = document_service.get_reference_documents(
            skip=pagination.offset,
            limit=pagination.size
        )
        total_count = document_service.get_reference_documents_count()
        
        document_responses = [ReferenceDocumentResponse.from_orm(doc) for doc in documents]
        metadata = create_response_metadata(pagination.page, pagination.size, total_count, len(documents))
        
        return PaginatedResponse(
            message="Reference documents retrieved successfully",
            data=document_responses,
            pagination=metadata.pagination
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
    document_service = DocumentService(db)
    
    try:
        document_service.delete_reference_document(document_id)
        return BaseResponse(message="Reference document deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
