from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    database_url: str
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "plagiarism_detector"
    database_user: str = "postgres"
    database_password: str = "postgres"
    
    # JWT Configuration
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket_name: str = "plagiarism-documents"
    minio_secure: bool = False
    
    # Application Configuration
    app_name: str = "Plagiarism Detection System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
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
            "127.0.0.1", 
            "100.64.0.2"  # Add this private IP as a fallback
        ] if host is not None
    ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
