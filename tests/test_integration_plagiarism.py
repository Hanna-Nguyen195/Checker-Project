import pytest
import time
from fastapi.testclient import TestClient


class TestPlagiarismIntegration:
    """Integration tests for plagiarism detection functionality."""

    def test_plagiarism_check_flow(self, client: TestClient, auth_headers, sample_text_file):
        """Test complete plagiarism check flow."""
        # Upload a document first
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("plagiarism_test.txt", f, "text/plain")},
                data={"title": "Plagiarism Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Start plagiarism check
        check_response = client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": document_id}
        )
        
        assert check_response.status_code == 201
        data = check_response.json()
        assert data["success"] is True
        assert data["message"] == "Plagiarism check started successfully"
        assert data["data"]["user_document_id"] == document_id
        assert data["data"]["check_status"] in ["processing", "completed"]
        
        return data["data"]["id"]

    def test_plagiarism_check_without_auth(self, client: TestClient, sample_text_file):
        """Test plagiarism check without authentication."""
        response = client.post(
            "/plagiarism/check",
            json={"document_id": 1}
        )
        assert response.status_code == 401

    def test_plagiarism_check_nonexistent_document(self, client: TestClient, auth_headers):
        """Test plagiarism check with non-existent document."""
        response = client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": 99999}
        )
        assert response.status_code == 400

    def test_plagiarism_check_other_user_document(self, client: TestClient, auth_headers, create_test_admin, sample_text_file):
        """Test plagiarism check on another user's document."""
        # Create admin and upload document as admin
        admin_login = client.post(
            "/auth/login",
            data={
                "username": create_test_admin.username,
                "password": "AdminPass123!"
            }
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=admin_headers,
                files={"file": ("admin_doc.txt", f, "text/plain")},
                data={"title": "Admin Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Try to check admin's document with regular user token
        response = client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": document_id}
        )
        assert response.status_code == 400

    def test_get_plagiarism_checks(self, client: TestClient, auth_headers, sample_text_file):
        """Test retrieving plagiarism checks."""
        # Upload document and start check
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("check_list_test.txt", f, "text/plain")},
                data={"title": "Check List Test"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": document_id}
        )
        
        # Get checks
        response = client.get("/plagiarism/checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert "pagination" in data

    def test_get_plagiarism_checks_pagination(self, client: TestClient, auth_headers, sample_text_file):
        """Test plagiarism checks pagination."""
        # Create multiple checks
        for i in range(3):
            with open(sample_text_file, 'rb') as f:
                upload_response = client.post(
                    "/documents/upload",
                    headers=auth_headers,
                    files={"file": ("pagination_test.txt", f, "text/plain")},
                    data={"title": f"Pagination Test {i}"}
                )
            
            document_id = upload_response.json()["data"]["id"]
            client.post(
                "/plagiarism/check",
                headers=auth_headers,
                json={"document_id": document_id}
            )
        
        # Test pagination
        response = client.get("/plagiarism/checks?page=1&size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["size"] == 2

    def test_get_specific_plagiarism_check(self, client: TestClient, auth_headers, sample_text_file):
        """Test retrieving a specific plagiarism check."""
        # Upload document and start check
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("specific_check.txt", f, "text/plain")},
                data={"title": "Specific Check Test"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        check_response = client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": document_id}
        )
        
        check_id = check_response.json()["data"]["id"]
        
        # Get specific check
        response = client.get(f"/plagiarism/checks/{check_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == check_id

    def test_get_nonexistent_plagiarism_check(self, client: TestClient, auth_headers):
        """Test retrieving non-existent plagiarism check."""
        response = client.get("/plagiarism/checks/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_other_user_plagiarism_check(self, client: TestClient, auth_headers, create_test_admin, sample_text_file):
        """Test accessing another user's plagiarism check."""
        # Create admin and perform check as admin
        admin_login = client.post(
            "/auth/login",
            data={
                "username": create_test_admin.username,
                "password": "AdminPass123!"
            }
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=admin_headers,
                files={"file": ("admin_check.txt", f, "text/plain")},
                data={"title": "Admin Check"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        check_response = client.post(
            "/plagiarism/check",
            headers=admin_headers,
            json={"document_id": document_id}
        )
        
        check_id = check_response.json()["data"]["id"]
        
        # Try to access admin's check with regular user token
        response = client.get(f"/plagiarism/checks/{check_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_plagiarism_report_generation(self, client: TestClient, auth_headers, sample_text_file):
        """Test plagiarism report generation."""
        # Upload document and start check
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("report_test.txt", f, "text/plain")},
                data={"title": "Report Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        check_response = client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": document_id}
        )
        
        check_id = check_response.json()["data"]["id"]
        
        # Wait a moment for processing (in real scenario, this might be async)
        time.sleep(1)
        
        # Get detailed report
        response = client.get(f"/plagiarism/checks/{check_id}/report", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "check" in data["data"]
        assert "document" in data["data"]
        assert "matches" in data["data"]
        
        # Verify report structure
        check_data = data["data"]["check"]
        assert "total_similarity_score" in check_data
        assert "check_status" in check_data
        assert "processing_time" in check_data

    def test_plagiarism_check_with_reference_documents(self, client: TestClient, auth_headers, admin_auth_headers, sample_text_file):
        """Test plagiarism check with reference documents in database."""
        # First, create a reference document as admin
        with open(sample_text_file, 'rb') as f:
            ref_response = client.post(
                "/admin/reference-documents",
                headers=admin_auth_headers,
                files={"file": ("reference.txt", f, "text/plain")},
                data={"title": "Reference Document"}
            )
        
        assert ref_response.status_code == 201
        
        # Now upload a user document with similar content
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("user_doc.txt", f, "text/plain")},
                data={"title": "User Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Start plagiarism check
        check_response = client.post(
            "/plagiarism/check",
            headers=auth_headers,
            json={"document_id": document_id}
        )
        
        assert check_response.status_code == 201
        check_id = check_response.json()["data"]["id"]
        
        # Wait for processing
        time.sleep(2)
        
        # Get report and verify it found matches
        report_response = client.get(f"/plagiarism/checks/{check_id}/report", headers=auth_headers)
        assert report_response.status_code == 200
        
        report_data = report_response.json()["data"]
        check_info = report_data["check"]
        
        # Should have processed at least one reference document
        assert check_info["reference_documents_count"] >= 1
        
        # Since we used the same file, similarity should be high
        if check_info["matches_found"] > 0:
            assert check_info["total_similarity_score"] > 0

    def test_multiple_concurrent_checks(self, client: TestClient, auth_headers, sample_text_file):
        """Test handling multiple concurrent plagiarism checks."""
        check_ids = []
        
        # Start multiple checks
        for i in range(3):
            with open(sample_text_file, 'rb') as f:
                upload_response = client.post(
                    "/documents/upload",
                    headers=auth_headers,
                    files={"file": ("concurrent_test.txt", f, "text/plain")},
                    data={"title": f"Concurrent Test {i}"}
                )
            
            document_id = upload_response.json()["data"]["id"]
            
            check_response = client.post(
                "/plagiarism/check",
                headers=auth_headers,
                json={"document_id": document_id}
            )
            
            assert check_response.status_code == 201
            check_ids.append(check_response.json()["data"]["id"])
        
        # Verify all checks were created
        assert len(check_ids) == 3
        
        # Wait for processing
        time.sleep(3)
        
        # Verify all checks completed or are processing
        for check_id in check_ids:
            response = client.get(f"/plagiarism/checks/{check_id}", headers=auth_headers)
            assert response.status_code == 200
            status = response.json()["data"]["check_status"]
            assert status in ["processing", "completed", "failed"]
