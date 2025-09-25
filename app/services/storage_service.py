from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
import structlog
import threading
import os

from app.config.settings import get_settings
from app.core.exceptions import StorageException
from app.utils.helpers import generate_unique_filename

settings = get_settings()
logger = structlog.get_logger(__name__)


class StorageService:
    """Service for handling file storage operations with MinIO."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StorageService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    # def __init__(self):
    #     if not self._initialized:
    #         self.client = None
    #         self.bucket_name = settings.minio_bucket_name
    #         self.is_connected = False
    #         self._initialize_client()
    #         self._initialized = True
    
    def __init__(self):
        if not self._initialized:
            self.client = None
            self.bucket_name = settings.minio_bucket_name
            self.is_connected = False
            try:
                self._initialize_client()
            except Exception as e:
                logger.error(f"Storage service initialization failed: {e}")
                self.client = None
                self.is_connected = False
            self._initialized = True

    def _should_skip_minio(self) -> bool:
        """Determine if MinIO initialization should be skipped."""
        # Check if we're in local environment first
        is_local = getattr(settings, 'is_local_environment', False)
        
        # Log the current environment and MinIO settings
        logger.info(
            "MinIO initialization check",
            is_local=is_local,
            minio_endpoint=settings.minio_endpoint,
            has_access_key=bool(settings.minio_access_key),
            has_secret_key=bool(settings.minio_secret_key),
            railway_env=os.getenv("RAILWAY_ENVIRONMENT_NAME"),
        )
        
        # Don't skip if we're in local environment and have localhost endpoint
        if is_local and settings.minio_endpoint in ["localhost:9000", "localhost:9090"]:
            logger.info("Local environment with localhost MinIO - will attempt connection")
            return False
            
        # Don't skip if we have proper MinIO configuration (Railway or external)
        if settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key:
            logger.info("MinIO configuration available - will attempt connection")
            return False
            
        # Skip if no MinIO endpoint configured
        if not settings.minio_endpoint:
            logger.info("Skipping MinIO initialization - no MinIO endpoint configured")
            return True
                
        return False
    
    def _initialize_client(self):
        """Initialize MinIO client with connection validation."""
        # Log current MinIO configuration for debugging
        logger.info(
            "MinIO configuration",
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            bucket=settings.minio_bucket_name,
            secure=settings.minio_secure,
            is_local=getattr(settings, 'is_local_environment', 'unknown')
        )
        
        # Skip MinIO initialization if we detect it will fail
        if self._should_skip_minio():
            self.is_connected = False
            self.client = None
            return
            
        # Skip socket connection check if we're on Railway
        # Railway services communicate over HTTPS, so socket check won't work
        if os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_PROJECT_ID"):
            logger.info(
                "Railway environment detected, skipping socket connectivity check",
                endpoint=settings.minio_endpoint
            )
        else:
            # Only perform socket check in non-Railway environments
            import socket
            try:
                # Handle endpoint with or without port
                if ':' in settings.minio_endpoint:
                    host, port_str = settings.minio_endpoint.split(':')
                    port = int(port_str)
                else:
                    # Default to port 443 for HTTPS if no port specified
                    host = settings.minio_endpoint
                    port = 443 if settings.minio_secure else 80
                    
                logger.info(f"Testing socket connection to {host}:{port}")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)  # 3 second timeout
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result != 0:
                    logger.warning(
                        "MinIO endpoint not reachable, skipping client creation",
                        endpoint=settings.minio_endpoint,
                        host=host,
                        port=port,
                        result=result
                    )
                    self.is_connected = False
                    self.client = None
                    return
                    
            except Exception as e:
                logger.warning(
                    "Failed to test MinIO endpoint connectivity",
                    endpoint=settings.minio_endpoint,
                    error=str(e)
                )
                self.is_connected = False
                self.client = None
                return
            
        # Create MinIO client
        client = None
        try:
            # Log the MinIO connection parameters (without secrets)
            logger.info(
                "Creating MinIO client",
                endpoint=settings.minio_endpoint,
                secure=settings.minio_secure,
                has_access_key=bool(settings.minio_access_key),
                has_secret_key=bool(settings.minio_secret_key),
                bucket_name=settings.minio_bucket_name
            )
            
            # Create the MinIO client
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure
            )
            
            # Test connection by listing buckets
            logger.info("Testing MinIO connection by listing buckets")
            buckets = list(client.list_buckets())
            logger.info(f"Found {len(buckets)} buckets")

            # Only assign to self.client if connection succeeds
            self.client = client
            self.is_connected = True
            self._ensure_bucket_exists()
            
            logger.info(
                "MinIO connection established successfully",
                endpoint=settings.minio_endpoint,
                bucket=self.bucket_name,
                secure=settings.minio_secure
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize MinIO client after connectivity test",
                endpoint=settings.minio_endpoint,
                error=str(e)
            )
            self.is_connected = False
            self.client = None
            client = None
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info("Created MinIO bucket", bucket=self.bucket_name)
        except S3Error as e:
            logger.error("Failed to create bucket", bucket=self.bucket_name, error=str(e))
            raise StorageException(f"Failed to create storage bucket: {e}")
    
    def _retry_connection(self):
        """Attempt to reconnect to MinIO."""
        if not self.is_connected and self.client is None:
            logger.info("Attempting to reconnect to MinIO")
            self._initialize_client()
    
    def upload_file(
        self, 
        file_data: BinaryIO, 
        original_filename: str,
        content_type: str,
        file_size: int
    ) -> str:
        """Upload a file and return the object ID."""
        # Remove the mock storage logic since we have proper MinIO config now
            
        # Try to reconnect if not connected
        if not self.is_connected:
            self._retry_connection()
            
        if not self.is_connected or not self.client:
            raise StorageException("MinIO storage is not available. Please check your MinIO configuration.")
            
        try:
            object_id = generate_unique_filename(original_filename)
            
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_id,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            
            logger.info(
                "File uploaded successfully",
                object_id=object_id,
                original_filename=original_filename,
                size=file_size
            )
            
            return object_id
            
        except S3Error as e:
            logger.error("Failed to upload file", error=str(e))
            raise StorageException(f"Failed to upload file: {e}")
    
    def download_file(self, object_id: str) -> bytes:
        """Download a file by object ID."""
        if not self.is_connected or not self.client:
            raise StorageException("MinIO storage is not available. Please check your MinIO configuration.")
            
        try:
            response = self.client.get_object(self.bucket_name, object_id)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info("File downloaded successfully", object_id=object_id)
            return data
            
        except S3Error as e:
            logger.error("Failed to download file", object_id=object_id, error=str(e))
            raise StorageException(f"Failed to download file: {e}")
    
    def delete_file(self, object_id: str) -> bool:
        """Delete a file by object ID."""
        if not self.is_connected or not self.client:
            raise StorageException("MinIO storage is not available. Please check your MinIO configuration.")
            
        try:
            self.client.remove_object(self.bucket_name, object_id)
            logger.info("File deleted successfully", object_id=object_id)
            return True
            
        except S3Error as e:
            logger.error("Failed to delete file", object_id=object_id, error=str(e))
            raise StorageException(f"Failed to delete file: {e}")
    
    def get_file_info(self, object_id: str) -> Optional[dict]:
        """Get file information by object ID."""
        try:
            stat = self.client.stat_object(self.bucket_name, object_id)
            return {
                "object_id": object_id,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag
            }
            
        except S3Error as e:
            logger.error("Failed to get file info", object_id=object_id, error=str(e))
            return None
    
    def file_exists(self, object_id: str) -> bool:
        """Check if a file exists."""
        try:
            self.client.stat_object(self.bucket_name, object_id)
            return True
        except S3Error:
            return False
