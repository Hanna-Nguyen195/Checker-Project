import pytest
import io
from fastapi.testclient import TestClient


class TestStorageIntegration:
    """Integration tests for MinIO storage functionality."""

    def test_storage_service_connection(self, storage_service):
        """Test MinIO storage service connection."""
        # This test verifies that the storage service can connect to MinIO
        # The bucket creation is tested in the service initialization
        assert storage_service is not None
        assert storage_service.client is not None
        assert storage_service.bucket_name == "test-documents"

    def test_file_upload_to_storage(self, storage_service):
        """Test direct file upload to storage."""
        test_content = b"This is a test file for storage integration"
        file_stream = io.BytesIO(test_content)
        
        object_id = storage_service.upload_file(
            file_data=file_stream,
            original_filename="test_storage.txt",
            content_type="text/plain",
            file_size=len(test_content)
        )
        
        assert object_id is not None
        assert storage_service.file_exists(object_id)
        
        # Cleanup
        storage_service.delete_file(object_id)

    def test_file_download_from_storage(self, storage_service):
        """Test file download from storage."""
        test_content = b"This is test content for download verification"
        file_stream = io.BytesIO(test_content)
        
        # Upload file
        object_id = storage_service.upload_file(
            file_data=file_stream,
            original_filename="download_test.txt",
            content_type="text/plain",
            file_size=len(test_content)
        )
        
        # Download and verify content
        downloaded_content = storage_service.download_file(object_id)
        assert downloaded_content == test_content
        
        # Cleanup
        storage_service.delete_file(object_id)

    def test_file_info_retrieval(self, storage_service):
        """Test file information retrieval from storage."""
        test_content = b"File info test content"
        file_stream = io.BytesIO(test_content)
        
        # Upload file
        object_id = storage_service.upload_file(
            file_data=file_stream,
            original_filename="info_test.txt",
            content_type="text/plain",
            file_size=len(test_content)
        )
        
        # Get file info
        file_info = storage_service.get_file_info(object_id)
        assert file_info is not None
        assert file_info["object_id"] == object_id
        assert file_info["size"] == len(test_content)
        assert "last_modified" in file_info
        
        # Cleanup
        storage_service.delete_file(object_id)

    def test_file_deletion_from_storage(self, storage_service):
        """Test file deletion from storage."""
        test_content = b"Content to be deleted"
        file_stream = io.BytesIO(test_content)
        
        # Upload file
        object_id = storage_service.upload_file(
            file_data=file_stream,
            original_filename="delete_test.txt",
            content_type="text/plain",
            file_size=len(test_content)
        )
        
        # Verify file exists
        assert storage_service.file_exists(object_id)
        
        # Delete file
        result = storage_service.delete_file(object_id)
        assert result is True
        
        # Verify file no longer exists
        assert not storage_service.file_exists(object_id)

    def test_nonexistent_file_operations(self, storage_service):
        """Test operations on non-existent files."""
        fake_object_id = "nonexistent-file-id"
        
        # File should not exist
        assert not storage_service.file_exists(fake_object_id)
        
        # Getting info should return None
        file_info = storage_service.get_file_info(fake_object_id)
        assert file_info is None
        
        # Download should raise exception
        with pytest.raises(Exception):
            storage_service.download_file(fake_object_id)

    def test_large_file_handling(self, storage_service):
        """Test handling of larger files."""
        # Create a 1MB test file
        large_content = b"x" * (1024 * 1024)
        file_stream = io.BytesIO(large_content)
        
        # Upload large file
        object_id = storage_service.upload_file(
            file_data=file_stream,
            original_filename="large_test.txt",
            content_type="text/plain",
            file_size=len(large_content)
        )
        
        # Verify upload
        assert storage_service.file_exists(object_id)
        
        # Download and verify content
        downloaded_content = storage_service.download_file(object_id)
        assert len(downloaded_content) == len(large_content)
        assert downloaded_content == large_content
        
        # Cleanup
        storage_service.delete_file(object_id)

    def test_multiple_file_operations(self, storage_service):
        """Test multiple concurrent file operations."""
        files_data = []
        object_ids = []
        
        # Upload multiple files
        for i in range(5):
            content = f"Test file content {i}".encode()
            file_stream = io.BytesIO(content)
            
            object_id = storage_service.upload_file(
                file_data=file_stream,
                original_filename=f"multi_test_{i}.txt",
                content_type="text/plain",
                file_size=len(content)
            )
            
            files_data.append(content)
            object_ids.append(object_id)
        
        # Verify all files exist
        for object_id in object_ids:
            assert storage_service.file_exists(object_id)
        
        # Download and verify all files
        for i, object_id in enumerate(object_ids):
            downloaded_content = storage_service.download_file(object_id)
            assert downloaded_content == files_data[i]
        
        # Cleanup all files
        for object_id in object_ids:
            storage_service.delete_file(object_id)
            assert not storage_service.file_exists(object_id)
