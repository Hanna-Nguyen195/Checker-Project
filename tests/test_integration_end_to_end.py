import pytest
import time
from fastapi.testclient import TestClient


class TestEndToEndIntegration:
    """End-to-end integration tests covering complete user workflows."""

    def test_complete_user_workflow(self, client: TestClient, sample_text_file):
        """Test complete user workflow from registration to plagiarism check."""
        # 1. User Registration
        user_data = {
            "username": "e2euser",
            "email": "e2e@example.com",
            "password": "E2EPass123!",
            "full_name": "End to End User"
        }
        
        register_response = client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201
        
        # 2. User Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Get User Profile
        profile_response = client.get("/users/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["username"] == user_data["username"]
        
        # 4. Upload Document
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=headers,
                files={"file": ("e2e_test.txt", f, "text/plain")},
                data={"title": "E2E Test Document"}
            )
        assert upload_response.status_code == 201
        document_id = upload_response.json()["data"]["id"]
        
        # 5. List User Documents
        docs_response = client.get("/documents", headers=headers)
        assert docs_response.status_code == 200
        assert len(docs_response.json()["data"]) > 0
        
        # 6. Start Plagiarism Check
        check_response = client.post(
            "/plagiarism/check",
            headers=headers,
            json={"document_id": document_id}
        )
        assert check_response.status_code == 201
        check_id = check_response.json()["data"]["id"]
        
        # 7. Get Plagiarism Check Status
        time.sleep(1)  # Wait for processing
        status_response = client.get(f"/plagiarism/checks/{check_id}", headers=headers)
        assert status_response.status_code == 200
        
        # 8. Get Detailed Report
        report_response = client.get(f"/plagiarism/checks/{check_id}/report", headers=headers)
        assert report_response.status_code == 200
        
        # 9. Download Original Document
        download_response = client.get(f"/documents/{document_id}/download", headers=headers)
        assert download_response.status_code == 200
        
        # 10. List All Checks
        checks_response = client.get("/plagiarism/checks", headers=headers)
        assert checks_response.status_code == 200
        assert len(checks_response.json()["data"]) > 0

    def test_complete_admin_workflow(self, client: TestClient, sample_text_file):
        """Test complete admin workflow."""
        # 1. Create Admin User
        admin_data = {
            "username": "e2eadmin",
            "email": "e2eadmin@example.com",
            "password": "AdminPass123!",
            "full_name": "E2E Admin User",
            "role": "admin"
        }
        
        admin_register_response = client.post("/auth/register", json=admin_data)
        assert admin_register_response.status_code == 201
        
        # 2. Admin Login
        admin_login_response = client.post(
            "/auth/login",
            data={
                "username": admin_data["username"],
                "password": admin_data["password"]
            }
        )
        assert admin_login_response.status_code == 200
        admin_token = admin_login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 3. Create Regular User for Testing
        user_data = {
            "username": "regularuser",
            "email": "regular@example.com",
            "password": "UserPass123!",
            "full_name": "Regular User"
        }
        
        user_register_response = client.post("/auth/register", json=user_data)
        assert user_register_response.status_code == 201
        
        user_login_response = client.post(
            "/auth/login",
            data={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        user_token = user_login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # 4. User Uploads Document
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=user_headers,
                files={"file": ("admin_workflow_test.txt", f, "text/plain")},
                data={"title": "Admin Workflow Test"}
            )
        document_id = upload_response.json()["data"]["id"]
        
        # 5. Admin Views System Stats
        stats_response = client.get("/admin/stats", headers=admin_headers)
        assert stats_response.status_code == 200
        
        # 6. Admin Views All Users
        users_response = client.get("/admin/users", headers=admin_headers)
        assert users_response.status_code == 200
        
        # 7. Admin Views Pending Documents
        pending_response = client.get("/admin/documents/pending", headers=admin_headers)
        assert pending_response.status_code == 200
        
        # 8. Admin Approves Document
        approve_response = client.post(
            f"/admin/documents/{document_id}/approve",
            headers=admin_headers,
            json={"comment": "Approved for reference database"}
        )
        assert approve_response.status_code == 200
        
        # 9. Admin Creates Reference Document
        with open(sample_text_file, 'rb') as f:
            ref_response = client.post(
                "/admin/reference-documents",
                headers=admin_headers,
                files={"file": ("reference_doc.txt", f, "text/plain")},
                data={"title": "Admin Created Reference"}
            )
        assert ref_response.status_code == 201
        
        # 10. Admin Views Reference Documents
        ref_docs_response = client.get("/admin/reference-documents", headers=admin_headers)
        assert ref_docs_response.status_code == 200

    def test_document_approval_and_plagiarism_workflow(self, client: TestClient, sample_text_file):
        """Test workflow where document gets approved and then used in plagiarism check."""
        # Create admin and user
        admin_data = {
            "username": "workflowadmin",
            "email": "workflowadmin@example.com",
            "password": "AdminPass123!",
            "full_name": "Workflow Admin",
            "role": "admin"
        }
        
        user_data = {
            "username": "workflowuser",
            "email": "workflowuser@example.com",
            "password": "UserPass123!",
            "full_name": "Workflow User"
        }
        
        # Register both users
        client.post("/auth/register", json=admin_data)
        client.post("/auth/register", json=user_data)
        
        # Login both users
        admin_login = client.post("/auth/login", data={
            "username": admin_data["username"],
            "password": admin_data["password"]
        })
        user_login = client.post("/auth/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
        
        # User uploads document
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=user_headers,
                files={"file": ("workflow_doc.txt", f, "text/plain")},
                data={"title": "Workflow Document"}
            )
        document_id = upload_response.json()["data"]["id"]
        
        # Admin approves document (creates reference document)
        approve_response = client.post(
            f"/admin/documents/{document_id}/approve",
            headers=admin_headers,
            json={"comment": "Approved for workflow test"}
        )
        assert approve_response.status_code == 200
        
        # User uploads another similar document
        with open(sample_text_file, 'rb') as f:
            second_upload = client.post(
                "/documents/upload",
                headers=user_headers,
                files={"file": ("similar_doc.txt", f, "text/plain")},
                data={"title": "Similar Document"}
            )
        second_doc_id = second_upload.json()["data"]["id"]
        
        # Run plagiarism check on second document
        check_response = client.post(
            "/plagiarism/check",
            headers=user_headers,
            json={"document_id": second_doc_id}
        )
        assert check_response.status_code == 201
        check_id = check_response.json()["data"]["id"]
        
        # Wait for processing and get report
        time.sleep(2)
        report_response = client.get(f"/plagiarism/checks/{check_id}/report", headers=user_headers)
        assert report_response.status_code == 200
        
        # Should have found matches since we used the same file
        report_data = report_response.json()["data"]
        assert report_data["check"]["reference_documents_count"] > 0

    def test_error_handling_workflow(self, client: TestClient):
        """Test error handling in various scenarios."""
        # 1. Try to access protected endpoint without auth
        response = client.get("/users/me")
        assert response.status_code == 401
        
        # 2. Try to register with invalid data
        invalid_user = {
            "username": "a",  # Too short
            "email": "invalid-email",
            "password": "weak",
            "full_name": "Invalid User"
        }
        response = client.post("/auth/register", json=invalid_user)
        assert response.status_code == 422
        
        # 3. Try to login with wrong credentials
        response = client.post("/auth/login", data={
            "username": "nonexistent",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        
        # 4. Create valid user for further tests
        user_data = {
            "username": "erroruser",
            "email": "error@example.com",
            "password": "ErrorPass123!",
            "full_name": "Error Test User"
        }
        client.post("/auth/register", json=user_data)
        
        login_response = client.post("/auth/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # 5. Try to access non-existent document
        response = client.get("/documents/99999", headers=headers)
        assert response.status_code == 404
        
        # 6. Try to start plagiarism check on non-existent document
        response = client.post(
            "/plagiarism/check",
            headers=headers,
            json={"document_id": 99999}
        )
        assert response.status_code == 400
        
        # 7. Try to access admin endpoint with user token
        response = client.get("/admin/stats", headers=headers)
        assert response.status_code == 403

    def test_concurrent_operations(self, client: TestClient, sample_text_file):
        """Test concurrent operations by multiple users."""
        users = []
        
        # Create multiple users
        for i in range(3):
            user_data = {
                "username": f"concurrent{i}",
                "email": f"concurrent{i}@example.com",
                "password": "ConcurrentPass123!",
                "full_name": f"Concurrent User {i}"
            }
            
            client.post("/auth/register", json=user_data)
            login_response = client.post("/auth/login", data={
                "username": user_data["username"],
                "password": user_data["password"]
            })
            
            headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
            users.append(headers)
        
        # Each user uploads documents and starts checks
        check_ids = []
        for i, headers in enumerate(users):
            with open(sample_text_file, 'rb') as f:
                upload_response = client.post(
                    "/documents/upload",
                    headers=headers,
                    files={"file": ("concurrent_test.txt", f, "text/plain")},
                    data={"title": f"Concurrent Test {i}"}
                )
            
            document_id = upload_response.json()["data"]["id"]
            
            check_response = client.post(
                "/plagiarism/check",
                headers=headers,
                json={"document_id": document_id}
            )
            
            check_ids.append((check_response.json()["data"]["id"], headers))
        
        # Wait for all checks to complete
        time.sleep(3)
        
        # Verify all checks completed successfully
        for check_id, headers in check_ids:
            response = client.get(f"/plagiarism/checks/{check_id}", headers=headers)
            assert response.status_code == 200
            status = response.json()["data"]["check_status"]
            assert status in ["completed", "failed"]  # Should not be still processing
