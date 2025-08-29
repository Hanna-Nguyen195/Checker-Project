import hashlib
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving the extension."""
    file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''
    unique_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    if file_extension:
        return f"{timestamp}_{unique_id}.{file_extension}"
    return f"{timestamp}_{unique_id}"


def generate_reset_token() -> str:
    """Generate a secure reset token."""
    return secrets.token_urlsafe(32)


def hash_file_content(content: bytes) -> str:
    """Generate SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def calculate_similarity_percentage(matches: int, total_sentences: int) -> float:
    """Calculate similarity percentage."""
    if total_sentences == 0:
        return 0.0
    return round((matches / total_sentences) * 100, 2)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def create_response_metadata(
    page: int,
    size: int,
    total: int,
    data_count: int
) -> Dict[str, Any]:
    """Create pagination metadata for API responses."""
    total_pages = (total + size - 1) // size
    
    return {
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "count": data_count
        }
    }
