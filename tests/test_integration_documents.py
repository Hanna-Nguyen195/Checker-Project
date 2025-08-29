import pytest
import io
from fastapi.testclient import TestClient


class TestDocumentIntegration:
    """Integration tests for document management functionality."""

    def test_document_upload_flow(self, client: TestClient, auth_headers, sample_text_file):
        """Test complete document upload flow."""
        with open(sample_text_file, 'rb') as f:
            response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Document uploaded successfully"
        assert data["data"]["title"] == "Test Document"
        assert data["data"]["status"] == "pending"
        assert data["data"]["content_type"] == "text/plain"
        
        return data["data"]["id"]

    def test_document_upload_without_auth(self, client: TestClient, sample_text_file):
        """Test document upload without authentication."""
        with open(sample_text_file, 'rb') as f:
            response = client.post(
                "/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        assert response.status_code == 401

    def test_document_upload_invalid_file_type(self, client: TestClient, auth_headers):
        """Test upload with invalid file type."""
        fake_file = io.BytesIO(b"fake executable content")
        response = client.post(
            "/documents/upload",
            headers=auth_headers,
            files={"file": ("malware.exe", fake_file, "application/x-executable")},
            data={"title": "Malware File"}
        )
        
        assert response.status_code == 400

    def test_document_upload_oversized_file(self, client: TestClient, auth_headers):
        """Test upload with oversized file."""
        # Create a large file content (larger than test limit)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB, over test limit of 10MB
        large_file = io.BytesIO(large_content)
        
        response = client.post(
            "/documents/upload",
            headers=auth_headers,
            files={"file": ("large.txt", large_file, "text/plain")},
            data={"title": "Large Document"}
        )
        
        assert response.status_code == 400

    def test_get_user_documents(self, client: TestClient, auth_headers, sample_text_file):
        """Test retrieving user documents."""
        # Upload a document first
        with open(sample_text_file, 'rb') as f:
            client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        # Get documents
        response = client.get("/documents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert "pagination" in data

    def test_get_user_documents_with_pagination(self, client: TestClient, auth_headers, sample_text_file):
        """Test document pagination."""
        # Upload multiple documents
        for i in range(3):
            with open(sample_text_file, 'rb') as f:
                client.post(
                    "/documents/upload",
                    headers=auth_headers,
                    files={"file": ("test.txt", f, "text/plain")},
                    data={"title": f"Test Document {i}"}
                )
        
        # Test pagination
        response = client.get("/documents?page=1&size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["size"] == 2

    def test_get_user_documents_with_status_filter(self, client: TestClient, auth_headers, sample_text_file):
        """Test filtering documents by status."""
        # Upload a document
        with open(sample_text_file, 'rb') as f:
            client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        # Filter by pending status
        response = client.get("/documents?status_filter=pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for doc in data["data"]:
            assert doc["status"] == "pending"

    def test_get_specific_document(self, client: TestClient, auth_headers, sample_text_file):
        """Test retrieving a specific document."""
        # Upload a document first
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Get specific document
        response = client.get(f"/documents/{document_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == document_id

    def test_get_nonexistent_document(self, client: TestClient, auth_headers):
        """Test retrieving non-existent document."""
        response = client.get("/documents/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_other_user_document(self, client: TestClient, auth_headers, create_test_admin, sample_text_file):
        """Test accessing another user's document."""
        # Create admin auth headers
        admin_login = client.post(
            "/auth/login",
            data={
                "username": create_test_admin.username,
                "password": "AdminPass123!"
            }
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        # Upload document as admin
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=admin_headers,
                files={"file": ("admin_test.txt", f, "text/plain")},
                data={"title": "Admin Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Try to access admin's document with regular user token
        response = client.get(f"/documents/{document_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_document_download(self, client: TestClient, auth_headers, sample_text_file):
        """Test document download functionality."""
        # Upload a document first
        with open(sample_text_file, 'rb') as f:
            original_content = f.read()
            f.seek(0)
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Download the document
        response = client.get(f"/documents/{document_id}/download", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain"
        assert "content-disposition" in response.headers
        
        # Verify content matches
        downloaded_content = response.content
        assert downloaded_content == original_content

    def test_document_download_without_auth(self, client: TestClient, auth_headers, sample_text_file):
        """Test document download without authentication."""
        # Upload a document first
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Try to download without auth
        response = client.get(f"/documents/{document_id}/download")
        assert response.status_code == 401

    def test_document_delete(self, client: TestClient, auth_headers, sample_text_file):
        """Test document deletion."""
        # Upload a document first
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Delete the document
        response = client.delete(f"/documents/{document_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Document deleted successfully"
        
        # Verify document is deleted
        get_response = client.get(f"/documents/{document_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_document_delete_nonexistent(self, client: TestClient, auth_headers):
        """Test deleting non-existent document."""
        response = client.delete("/documents/99999", headers=auth_headers)
        assert response.status_code == 400

    def test_document_storage_integration(self, client: TestClient, auth_headers, sample_text_file, storage_service):
        """Test integration with MinIO storage service."""
        # Upload a document
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("storage_test.txt", f, "text/plain")},
                data={"title": "Storage Test Document"}
            )
        
        assert upload_response.status_code == 201
        document_data = upload_response.json()["data"]
        object_id = document_data["object_id"]
        
        # Verify file exists in storage
        assert storage_service.file_exists(object_id)
        
        # Verify file info
        file_info = storage_service.get_file_info(object_id)
        assert file_info is not None
        assert file_info["object_id"] == object_id
        
        # Delete document and verify storage cleanup
        document_id = document_data["id"]
        delete_response = client.delete(f"/documents/{document_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # Verify file is deleted from storage
        assert not storage_service.file_exists(object_id)
