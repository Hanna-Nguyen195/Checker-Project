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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    database: str = "disconnected"
    storage: str = "disconnected"
    status: str = "unhealthy"
    database_error: Optional[str] = None
    storage_error: Optional[str] = None
    
    def calculate_status(self) -> str:
        """Calculate overall status based on component statuses."""
        if self.database == "connected" and self.storage == "connected":
            return "healthy"
        elif self.database == "connected" or self.storage == "connected":
            return "degraded"
        else:
            return "unhealthy"
