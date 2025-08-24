import re
from typing import List, Optional
from fastapi import UploadFile
from app.config.settings import get_settings
from app.core.exceptions import ValidationException, FileUploadException

settings = get_settings()


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    """Validate password strength."""
    if len(password) < 8:
        return False
    
    # Check for at least one uppercase, lowercase, digit, and special character
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True


def validate_username(username: str) -> bool:
    """Validate username format."""
    if len(username) < 3 or len(username) > 50:
        return False
    
    # Allow alphanumeric characters, underscores, and hyphens
    pattern = r'^[a-zA-Z0-9_-]+$'
    return re.match(pattern, username) is not None


def validate_file_upload(file: UploadFile) -> None:
    """Validate uploaded file."""
    if not file.filename:
        raise FileUploadException("No file selected")
    
    # Check file size
    if file.size and file.size > settings.max_file_size:
        raise FileUploadException(
            f"File size exceeds maximum allowed size of {settings.max_file_size / (1024*1024):.1f}MB"
        )
    
    # Check file type
    if file.content_type not in settings.allowed_file_types:
        raise FileUploadException(
            f"File type {file.content_type} not allowed. "
            f"Allowed types: {', '.join(settings.allowed_file_types)}"
        )


def validate_pagination_params(page: int, size: int) -> None:
    """Validate pagination parameters."""
    if page < 1:
        raise ValidationException("Page number must be greater than 0")
    
    if size < 1 or size > settings.max_page_size:
        raise ValidationException(
            f"Page size must be between 1 and {settings.max_page_size}"
        )
