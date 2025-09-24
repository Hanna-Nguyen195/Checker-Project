from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model."""
   
    message: Optional[str] = None
    data: Optional[Any] = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int
    size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool
    count: int


class PaginatedResponse(BaseResponse):
    """Paginated response model."""
    data: List[Any]
    pagination: PaginationMeta
    sync_results: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    database: str = "connected"
    storage: str = "connected"
