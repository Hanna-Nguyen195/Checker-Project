import pytest
import time
from fastapi.testclient import TestClient


class TestAdminIntegration:
    """Integration tests for admin functionality."""

    def test_admin_system_stats(self, client: TestClient, admin_auth_headers):
        """Test admin system statistics endpoint."""
        response = client.get("/admin/stats", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        stats = data["data"]
        assert "users" in stats
        assert "documents" in stats
        assert "plagiarism_checks" in stats
        assert "generated_at" in stats
        
        # Verify user stats structure
        user_stats = stats["users"]
        assert "total" in user_stats
        assert "active" in user_stats
        assert "admins" in user_stats
        
        # Verify document stats structure
        doc_stats = stats["documents"]
        assert "user_documents" in doc_stats
        assert "reference_documents" in doc_stats

    def test_admin_stats_unauthorized(self, client: TestClient, auth_headers):
        """Test admin stats access with regular user token."""
        response = client.get("/admin/stats", headers=auth_headers)
        assert response.status_code == 403

    def test_admin_activity_stats(self, client: TestClient, admin_auth_headers):
        """Test admin activity statistics."""
        response = client.get("/admin/stats/activity?days=7", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_admin_similarity_distribution(self, client: TestClient, admin_auth_headers):
        """Test similarity distribution statistics."""
        response = client.get("/admin/stats/similarity-distribution", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        distribution = data["data"]
        expected_ranges = ["0-10%", "11-25%", "26-50%", "51-75%", "76-90%", "91-100%"]
        for range_key in expected_ranges:
            assert range_key in distribution
            assert isinstance(distribution[range_key], int)

    def test_admin_get_all_users(self, client: TestClient, admin_auth_headers, create_test_user):
        """Test admin getting all users."""
        response = client.get("/admin/users", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert "pagination" in data
        
        # Verify user data structure
        user = data["data"][0]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "role" in user
        assert "status" in user

    def test_admin_get_users_pagination(self, client: TestClient, admin_auth_headers):
        """Test admin user list pagination."""
        response = client.get("/admin/users?page=1&size=5", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["size"] == 5

    def test_admin_update_user(self, client: TestClient, admin_auth_headers, create_test_user):
        """Test admin updating user information."""
        user_id = create_test_user.id
        
        update_data = {
            "full_name": "Updated Full Name",
            "status": "banned"
        }
        
        response = client.put(f"/admin/users/{user_id}", headers=admin_auth_headers, json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["full_name"] == "Updated Full Name"
        assert data["data"]["status"] == "banned"

    def test_admin_ban_user(self, client: TestClient, admin_auth_headers, create_test_user):
        """Test admin banning a user."""
        user_id = create_test_user.id
        
        response = client.post(f"/admin/users/{user_id}/ban", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "banned"

    def test_admin_unban_user(self, client: TestClient, admin_auth_headers, create_test_user):
        """Test admin unbanning a user."""
        user_id = create_test_user.id
        
        # First ban the user
        client.post(f"/admin/users/{user_id}/ban", headers=admin_auth_headers)
        
        # Then unban
        response = client.post(f"/admin/users/{user_id}/unban", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "active"

    def test_admin_get_pending_documents(self, client: TestClient, admin_auth_headers, auth_headers, sample_text_file):
        """Test admin getting pending document approvals."""
        # Upload a document as regular user (will be pending)
        with open(sample_text_file, 'rb') as f:
            client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("pending_test.txt", f, "text/plain")},
                data={"title": "Pending Test Document"}
            )
        
        # Get pending documents as admin
        response = client.get("/admin/documents/pending", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        
        # Verify all documents are pending
        for doc in data["data"]:
            assert doc["status"] == "pending"

    def test_admin_pending_documents_summary(self, client: TestClient, admin_auth_headers, auth_headers, sample_text_file):
        """Test admin pending documents summary."""
        # Upload a document to have pending items
        with open(sample_text_file, 'rb') as f:
            client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("summary_test.txt", f, "text/plain")},
                data={"title": "Summary Test Document"}
            )
        
        response = client.get("/admin/documents/pending/summary", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        summary = data["data"]
        assert "total_pending" in summary
        assert "by_content_type" in summary
        assert summary["total_pending"] > 0

    def test_admin_approve_document(self, client: TestClient, admin_auth_headers, auth_headers, sample_text_file):
        """Test admin approving a user document."""
        # Upload a document as regular user
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("approve_test.txt", f, "text/plain")},
                data={"title": "Approve Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Approve the document as admin
        approval_data = {"comment": "Document approved for testing"}
        response = client.post(
            f"/admin/documents/{document_id}/approve",
            headers=admin_auth_headers,
            json=approval_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "approved"
        assert data["data"]["comment"] == "Document approved for testing"

    def test_admin_reject_document(self, client: TestClient, admin_auth_headers, auth_headers, sample_text_file):
        """Test admin rejecting a user document."""
        # Upload a document as regular user
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("reject_test.txt", f, "text/plain")},
                data={"title": "Reject Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # Reject the document as admin
        rejection_data = {"comment": "Document rejected due to inappropriate content"}
        response = client.post(
            f"/admin/documents/{document_id}/reject",
            headers=admin_auth_headers,
            json=rejection_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "rejected"
        assert data["data"]["comment"] == "Document rejected due to inappropriate content"

    def test_admin_create_reference_document(self, client: TestClient, admin_auth_headers, sample_text_file):
        """Test admin creating reference document directly."""
        with open(sample_text_file, 'rb') as f:
            response = client.post(
                "/admin/reference-documents",
                headers=admin_auth_headers,
                files={"file": ("reference_test.txt", f, "text/plain")},
                data={"title": "Test Reference Document"}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Reference Document"
        assert data["data"]["content_type"] == "text/plain"

    def test_admin_get_reference_documents(self, client: TestClient, admin_auth_headers, sample_text_file):
        """Test admin getting reference documents."""
        # Create a reference document first
        with open(sample_text_file, 'rb') as f:
            client.post(
                "/admin/reference-documents",
                headers=admin_auth_headers,
                files={"file": ("ref_list_test.txt", f, "text/plain")},
                data={"title": "Reference List Test"}
            )
        
        # Get reference documents
        response = client.get("/admin/reference-documents", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert "pagination" in data

    def test_admin_delete_reference_document(self, client: TestClient, admin_auth_headers, sample_text_file):
        """Test admin deleting reference document."""
        # Create a reference document first
        with open(sample_text_file, 'rb') as f:
            create_response = client.post(
                "/admin/reference-documents",
                headers=admin_auth_headers,
                files={"file": ("delete_ref_test.txt", f, "text/plain")},
                data={"title": "Delete Reference Test"}
            )
        
        document_id = create_response.json()["data"]["id"]
        
        # Delete the reference document
        response = client.delete(f"/admin/reference-documents/{document_id}", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Reference document deleted successfully"

    def test_admin_operations_unauthorized(self, client: TestClient, auth_headers):
        """Test admin operations with regular user token."""
        endpoints = [
            "/admin/users",
            "/admin/documents/pending",
            "/admin/reference-documents"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 403

    def test_admin_document_approval_workflow(self, client: TestClient, admin_auth_headers, auth_headers, sample_text_file):
        """Test complete document approval workflow."""
        # 1. User uploads document
        with open(sample_text_file, 'rb') as f:
            upload_response = client.post(
                "/documents/upload",
                headers=auth_headers,
                files={"file": ("workflow_test.txt", f, "text/plain")},
                data={"title": "Workflow Test Document"}
            )
        
        document_id = upload_response.json()["data"]["id"]
        
        # 2. Document should be pending
        doc_response = client.get(f"/documents/{document_id}", headers=auth_headers)
        assert doc_response.json()["data"]["status"] == "pending"
        
        # 3. Admin sees it in pending list
        pending_response = client.get("/admin/documents/pending", headers=admin_auth_headers)
        pending_docs = pending_response.json()["data"]
        assert any(doc["id"] == document_id for doc in pending_docs)
        
        # 4. Admin approves document
        approval_response = client.post(
            f"/admin/documents/{document_id}/approve",
            headers=admin_auth_headers,
            json={"comment": "Approved for reference database"}
        )
        assert approval_response.status_code == 200
        
        # 5. Document status should be updated
        updated_doc_response = client.get(f"/documents/{document_id}", headers=auth_headers)
        assert updated_doc_response.json()["data"]["status"] == "approved"
        
        # 6. Reference document should be created
        ref_docs_response = client.get("/admin/reference-documents", headers=admin_auth_headers)
        ref_docs = ref_docs_response.json()["data"]
        assert len(ref_docs) > 0
