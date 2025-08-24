import pytest
from fastapi.testclient import TestClient


class TestAuthenticationIntegration:
    """Integration tests for authentication functionality."""

    def test_user_registration_flow(self, client: TestClient):
        """Test complete user registration flow."""
        # Test user registration
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "full_name": "New User"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "User registered successfully"
        assert data["data"]["username"] == user_data["username"]
        assert data["data"]["email"] == user_data["email"]
        assert data["data"]["role"] == "user"
        assert data["data"]["status"] == "active"

    def test_duplicate_registration(self, client: TestClient):
        """Test registration with duplicate username/email."""
        user_data = {
            "username": "duplicate",
            "email": "duplicate@example.com",
            "password": "DupPass123!",
            "full_name": "Duplicate User"
        }
        
        # First registration should succeed
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Second registration with same username should fail
        response2 = client.post("/auth/register", json=user_data)
        assert response2.status_code == 409
        
        # Registration with same email but different username should fail
        user_data["username"] = "different"
        response3 = client.post("/auth/register", json=user_data)
        assert response3.status_code == 409

    def test_login_flow(self, client: TestClient, create_test_user):
        """Test complete login flow."""
        # Test successful login
        response = client.post(
            "/auth/login",
            data={
                "username": create_test_user.username,
                "password": "TestPass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user"]["username"] == create_test_user.username

    def test_login_with_email(self, client: TestClient, create_test_user):
        """Test login using email instead of username."""
        response = client.post(
            "/auth/login",
            data={
                "username": create_test_user.email,
                "password": "TestPass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_invalid_login_credentials(self, client: TestClient, create_test_user):
        """Test login with invalid credentials."""
        # Wrong password
        response = client.post(
            "/auth/login",
            data={
                "username": create_test_user.username,
                "password": "WrongPassword"
            }
        )
        assert response.status_code == 401
        
        # Non-existent user
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        assert response.status_code == 401

    def test_protected_endpoint_access(self, client: TestClient, auth_headers):
        """Test accessing protected endpoints with valid token."""
        response = client.get("/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data

    def test_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoints without token."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """Test accessing protected endpoints with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401

    def test_admin_endpoint_access(self, client: TestClient, admin_auth_headers):
        """Test admin endpoint access with admin token."""
        response = client.get("/admin/stats", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_admin_endpoint_with_user_token(self, client: TestClient, auth_headers):
        """Test admin endpoint access with regular user token."""
        response = client.get("/admin/stats", headers=auth_headers)
        assert response.status_code == 403

    def test_password_validation(self, client: TestClient):
        """Test password validation during registration."""
        # Weak password
        weak_password_data = {
            "username": "weakpass",
            "email": "weak@example.com",
            "password": "123",
            "full_name": "Weak Password User"
        }
        
        response = client.post("/auth/register", json=weak_password_data)
        assert response.status_code == 422

    def test_email_validation(self, client: TestClient):
        """Test email validation during registration."""
        invalid_email_data = {
            "username": "invalidemail",
            "email": "not-an-email",
            "password": "ValidPass123!",
            "full_name": "Invalid Email User"
        }
        
        response = client.post("/auth/register", json=invalid_email_data)
        assert response.status_code == 422

    def test_forgot_password_flow(self, client: TestClient, create_test_user):
        """Test forgot password functionality."""
        response = client.post(
            "/auth/forgot-password",
            params={"email": create_test_user.email}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # In test environment, token is returned for verification
        assert "reset_token" in data["data"]

    def test_forgot_password_nonexistent_email(self, client: TestClient):
        """Test forgot password with non-existent email."""
        response = client.post(
            "/auth/forgot-password",
            params={"email": "nonexistent@example.com"}
        )
        # Should return success to not reveal if email exists
        assert response.status_code == 200
