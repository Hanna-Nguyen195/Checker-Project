from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_pagination_params, PaginationParams
from app.services.plagiarism_service import PlagiarismService
from app.models.user import User
from app.schemas.plagiarism import (
    PlagiarismCheckCreate, 
    PlagiarismCheckResponse, 
    PlagiarismCheckDetailResponse
)
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.helpers import create_response_metadata

router = APIRouter()


@router.post("/check", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def start_plagiarism_check(
    check_data: PlagiarismCheckCreate,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Start plagiarism check for a document."""
    plagiarism_service = PlagiarismService(db)
    
    try:
        check = plagiarism_service.start_plagiarism_check(
            user_id=current_user.id,
            document_id=check_data.document_id
        )
        
        return BaseResponse(
            message="Plagiarism check started successfully",
            data=PlagiarismCheckResponse.from_orm(check)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/checks", response_model=PaginatedResponse)
async def get_plagiarism_checks(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's plagiarism checks with pagination."""
    plagiarism_service = PlagiarismService(db)
    
    checks = plagiarism_service.get_user_plagiarism_checks(
        user_id=current_user.id,
        skip=pagination.offset,
        limit=pagination.size
    )
    
    total_count = plagiarism_service.get_user_plagiarism_checks_count(current_user.id)
    
    check_responses = [PlagiarismCheckResponse.from_orm(check) for check in checks]
    metadata = create_response_metadata(pagination.page, pagination.size, total_count, len(checks))
    
    return PaginatedResponse(
        data=check_responses,
        pagination=metadata["pagination"]
    )


@router.get("/checks/{check_id}", response_model=BaseResponse)
async def get_plagiarism_check(
    check_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get plagiarism check details."""
    plagiarism_service = PlagiarismService(db)
    
    check = plagiarism_service.get_plagiarism_check(check_id, current_user.id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plagiarism check not found")
    
    return BaseResponse(
        data=PlagiarismCheckResponse.from_orm(check)
    )


@router.get("/checks/{check_id}/report", response_model=BaseResponse)
async def get_plagiarism_report(
    check_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get detailed plagiarism check report."""
    plagiarism_service = PlagiarismService(db)
    
    try:
        report = plagiarism_service.get_plagiarism_check_details(check_id, current_user.id)
        return BaseResponse(data=report)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
