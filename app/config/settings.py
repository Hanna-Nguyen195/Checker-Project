from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache
import os
from urllib.parse import urlparse


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # env_file=[".env", ".env.railway"],
        env_file=[".env"],
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    database_url: str 
    database_host: str = "localhost"
    database_port: int = 5433
    
    @property
    def database_name(self) -> str:
        """Parse database name from database_url."""
        parsed = urlparse(self.database_url)
        return parsed.path.lstrip('/')
    
    @property
    def database_user(self) -> str:
        """Parse database user from database_url."""
        parsed = urlparse(self.database_url)
        return parsed.username or ""
    
    @property
    def database_password(self) -> str:
        """Parse database password from database_url."""
        parsed = urlparse(self.database_url)
        return parsed.password or "" 
    
    # JWT Configuration
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # MinIO Configuration
    # Environment-aware MinIO configuration
    @property
    def is_local_environment(self) -> bool:
        """Check if running in local development environment."""
        return not any([
            os.getenv("RAILWAY_ENVIRONMENT_NAME"),
            os.getenv("RAILWAY_PROJECT_ID"),
            os.getenv("PORT"),
            self.environment == "production"
        ])
    
    @property
    def minio_endpoint(self) -> str:
        """Get MinIO endpoint based on environment."""
        if self.is_local_environment:
            return "localhost:9090"
        # For Railway, return None if no MinIO endpoint is configured
        return os.getenv("MINIO_ENDPOINT")
    
    @property
    def minio_access_key(self) -> str:
        """Get MinIO access key based on environment."""
        if self.is_local_environment:
            return "minioadmin"
        return os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    
    @property
    def minio_secret_key(self) -> str:
        """Get MinIO secret key based on environment."""
        if self.is_local_environment:
            return "minioadmin123"
        return os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    
    @property
    def minio_bucket_name(self) -> str:
        """Get MinIO bucket name."""
        return os.getenv("MINIO_BUCKET_NAME", "plagiarism")
    
    @property
    def minio_secure(self) -> bool:
        """Use HTTPS for MinIO in production environments."""
        return not self.is_local_environment
    
    # Application Configuration
    app_name: str = "Plagiarism Detection System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    enable_docs: bool = True  # Enable Swagger docs by default
    
    # CORS Configuration - using simple strings that will be split in middleware
    allowed_origins: str = "http://localhost:3000"
    allowed_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    allowed_headers: str = "*"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # File Upload Configuration
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: str = "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
    
    def get_allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(',')]
    
    def get_allowed_methods(self) -> List[str]:
        """Parse allowed methods from comma-separated string."""
        return [method.strip() for method in self.allowed_methods.split(',')]
    
    def get_allowed_headers(self) -> List[str]:
        """Parse allowed headers from comma-separated string."""
        return [header.strip() for header in self.allowed_headers.split(',')]
    
    def get_allowed_file_types(self) -> List[str]:
        """Parse allowed file types from comma-separated string."""
        return [file_type.strip() for file_type in self.allowed_file_types.split(',')]
    
    # Railway deployment configuration
    allowed_hosts: list[str] = [
        host for host in [
            os.getenv("RAILWAY_PUBLIC_DOMAIN"), 
            "localhost", 
            "127.0.0.1"
        ] if host is not None
    ]
    
    # Add a flag to allow all hosts if running on a trusted platform
    # Railway detection - be very aggressive since we're getting 400 errors
    allow_all_hosts: bool = True  # Temporarily disable host validation entirely


# @lru_cache()
def get_settings() -> Settings:
    return Settings()
