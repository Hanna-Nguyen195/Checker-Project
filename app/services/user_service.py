from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
import structlog
from datetime import datetime, timedelta

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import ConflictException, NotFoundException, AuthenticationException
from app.utils.helpers import generate_reset_token
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        import time
        
        start_time = time.time()
        
        # Check if username or email already exists
        logger.info("Checking for existing user", username=user_data.username, email=user_data.email)
        check_start = time.time()
        
        existing_user = self.db.query(User).filter(
            or_(User.username == user_data.username, User.email == user_data.email)
        ).first()
        
        check_duration = time.time() - check_start
        logger.info("User existence check completed", duration_seconds=round(check_duration, 3))
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise ConflictException("Username already exists")
            else:
                raise ConflictException("Email already exists")
        
        # Hash password
        logger.info("Starting password hashing")
        hash_start = time.time()
        password_hash = get_password_hash(user_data.password)
        hash_duration = time.time() - hash_start
        logger.info("Password hashing completed", duration_seconds=round(hash_duration, 3))
        
        # Create new user
        logger.info("Creating user object")
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            full_name=user_data.full_name,
            role=user_data.role,
            status=user_data.status
        )
        
        # Database operations
        logger.info("Starting database operations")
        db_start = time.time()
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        db_duration = time.time() - db_start
        total_duration = time.time() - start_time
        
        logger.info("User created successfully", 
                   user_id=db_user.id, 
                   username=db_user.username,
                   db_duration_seconds=round(db_duration, 3),
                   total_duration_seconds=round(total_duration, 3))
        return db_user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Get user by username or email."""
        return self.db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """Update user information."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        
        # Check for email conflicts if email is being updated
        if user_data.email and user_data.email != user.email:
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user:
                raise ConflictException("Email already exists")
        
        # Update user fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info("User updated successfully", user_id=user.id)
        return user
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationException("Current password is incorrect")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        self.db.commit()
        
        logger.info("Password changed successfully", user_id=user.id)
        return True
    
    def initiate_password_reset(self, email: str) -> str:
        """Initiate password reset process."""
        user = self.get_user_by_email(email)
        if not user:
            raise NotFoundException("User with this email not found")
        
        # Generate reset token
        reset_token = generate_reset_token()
        settings = get_settings()
        
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=settings.reset_token_expire_hours)
        
        self.db.commit()
        
        logger.info("Password reset initiated", user_id=user.id, email=email)
        return reset_token
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        user = self.db.query(User).filter(User.reset_token == token).first()
        if not user:
            raise NotFoundException("Invalid reset token")
        
        # Check if token has expired
        if user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow():
            # Clear expired token
            user.reset_token = None
            user.reset_token_expiry = None
            self.db.commit()
            raise NotFoundException("Reset token has expired")
        
        # Update password and clear reset token
        user.password_hash = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        
        self.db.commit()
        
        logger.info("Password reset successfully", user_id=user.id)
        return True
    
    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def get_users_count(self) -> int:
        """Get total count of users."""
        return self.db.query(User).count()
    
    def ban_user(self, user_id: int) -> User:
        """Ban a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        
        user.status = "banned"
        self.db.commit()
        self.db.refresh(user)
        
        logger.info("User banned", user_id=user.id)
        return user
    
    def unban_user(self, user_id: int) -> User:
        """Unban a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        
        user.status = "active"
        self.db.commit()
        self.db.refresh(user)
        
        logger.info("User unbanned", user_id=user.id)
        return user
