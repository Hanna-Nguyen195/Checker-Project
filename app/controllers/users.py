from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_pagination_params, PaginationParams
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, UserPasswordChange
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.helpers import create_response_metadata

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user_dependency)):
    """Get current user profile."""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=BaseResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    user_service = UserService(db)
    
    try:
        updated_user = user_service.update_user(current_user.id, user_data)
        return BaseResponse(
            message="Profile updated successfully",
            data=UserResponse.from_orm(updated_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    password_data: UserPasswordChange,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Change user password."""
    user_service = UserService(db)
    
    try:
        user_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password
        )
        return BaseResponse(message="Password changed successfully")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
