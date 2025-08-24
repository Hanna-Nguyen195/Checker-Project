from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import os

from app.config.settings import get_settings
from app.config.database import create_tables
from app.core.middleware import LoggingMiddleware, setup_cors_middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.exceptions import BaseCustomException
from app.utils.logger import configure_logging
from app.schemas.common import HealthCheck, ErrorResponse

# Import routers
from app.controllers import auth, users, documents, plagiarism, admin

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    configure_logging()
    logger.info("Starting plagiarism detection system", version=settings.app_version)
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        # Allow app to start without database for testing
        logger.warning("Application starting without database connection")
    
    yield
    
    # Shutdown
    logger.info("Shutting down plagiarism detection system")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive plagiarism detection system with document management and analytics",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)



# Setup trusted host middleware directly
railway_vars = {
    "RAILWAY_ENVIRONMENT_NAME": os.getenv("RAILWAY_ENVIRONMENT_NAME"),
    "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT"),
    "RAILWAY_PROJECT_ID": os.getenv("RAILWAY_PROJECT_ID"),
    "PORT": os.getenv("PORT")
}
logger.info("Railway environment check", railway_vars=railway_vars, allow_all_hosts=settings.allow_all_hosts)

if settings.allow_all_hosts:
    logger.info("✅ SKIPPING TrustedHostMiddleware - Railway deployment detected")
    # Don't add TrustedHostMiddleware on Railway - let all hosts through
else:
    # Filter out None values for local development
    allowed_hosts = [host for host in settings.allowed_hosts if host is not None]
    logger.info("⚠️ Adding TrustedHostMiddleware for local development", allowed_hosts=allowed_hosts)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Setup middleware
setup_cors_middleware(app)
app.add_middleware(LoggingMiddleware)


# Global exception handler
@app.exception_handler(BaseCustomException)
async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """Handle custom exceptions."""
    logger.error(
        "Custom exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            error_code=exc.__class__.__name__
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error" if not settings.debug else str(exc),
            error_code="InternalServerError"
        ).dict()
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        version=settings.app_version,
        database="connected",
        storage="connected"
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(plagiarism.router, prefix="/plagiarism", tags=["Plagiarism"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.debug
    )
