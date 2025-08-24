from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import get_settings
from app.core.security import authenticate_user, create_access_token
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse, UserPasswordReset
from app.schemas.common import BaseResponse
from app.core.exceptions import AuthenticationException, ConflictException
import time
import structlog


router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""

    
    logger = structlog.get_logger(__name__)
    start_time = time.time()
    
    logger.info("Starting user registration", username=user_data.username, email=user_data.email)
    
    user_service = UserService(db)
    
    try:
        logger.info("Creating user via service")
        user = user_service.create_user(user_data)
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info("User registration completed", 
                   user_id=user.id, 
                   duration_seconds=round(duration, 3))
        
        return BaseResponse(
            message="User registered successfully",
            data=UserResponse.from_orm(user)
        )
    except ConflictException as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error("User registration failed - conflict", 
                    error=str(e), 
                    duration_seconds=round(duration, 3))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise AuthenticationException("Incorrect username or password")
    
    if user.status != "active":
        raise AuthenticationException("Account is not active")
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.from_orm(user)
    )


@router.post("/forgot-password", response_model=BaseResponse)
async def forgot_password(email: str, db: Session = Depends(get_db)):
    """Initiate password reset."""
    user_service = UserService(db)
    
    try:
        reset_token = user_service.initiate_password_reset(email)
        # In production, send email with reset token
        return BaseResponse(
            message="Password reset instructions sent to your email",
            data={"reset_token": reset_token}  # Remove in production
        )
    except Exception as e:
        # Don't reveal if email exists or not
        return BaseResponse(message="If the email exists, reset instructions have been sent")


@router.post("/reset-password", response_model=BaseResponse)
async def reset_password(reset_data: UserPasswordReset, db: Session = Depends(get_db)):
    """Reset password using token."""
    user_service = UserService(db)
    
    try:
        user_service.reset_password(reset_data.token, reset_data.new_password)
        return BaseResponse(message="Password reset successfully")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
