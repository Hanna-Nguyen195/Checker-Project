from typing import Optional
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import get_settings
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User

settings = get_settings()


class PaginationParams:
    """Pagination parameters dependency."""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(
            settings.default_page_size,
            ge=1,
            le=settings.max_page_size,
            description="Page size"
        )
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


def get_pagination_params(
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size)
) -> PaginationParams:
    """Get pagination parameters."""
    return PaginationParams(page=page, size=size)


def get_current_user_dependency(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to get current user."""
    return current_user


def get_current_admin_dependency(
    current_admin: User = Depends(get_current_admin_user)
) -> User:
    """Dependency to get current admin user."""
    return current_admin


def get_db_dependency(db: Session = Depends(get_db)) -> Session:
    """Dependency to get database session."""
    return db
