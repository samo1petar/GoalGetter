"""
Tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import create_test_user_data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_signup_success(self, client: AsyncClient):
        """Test successful user registration."""
        user_data = create_test_user_data("signup_test@example.com")

        response = await client.post("/api/v1/auth/signup", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["name"] == user_data["name"]
        assert "password" not in data["user"]

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with existing email."""
        user_data = {
            "email": test_user["email"],  # Already exists
            "name": "Another User",
            "password": "AnotherPassword123!",
        }

        response = await client.post("/api/v1/auth/signup", json=user_data)

        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data.get("detail", "").lower() or \
               "already registered" in data.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_signup_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        user_data = {
            "email": "invalid-email",
            "name": "Test User",
            "password": "TestPassword123!",
        }

        response = await client.post("/api/v1/auth/signup", json=user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "email": "weak_pass@example.com",
            "name": "Test User",
            "password": "weak",  # Too short
        }

        response = await client.post("/api/v1/auth/signup", json=user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        login_data = {
            "email": test_user["email"],
            "password": test_user["password"],
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user["email"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password."""
        login_data = {
            "email": test_user["email"],
            "password": "WrongPassword123!",
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data.get("detail", "").lower() or \
               "incorrect" in data.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent email."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPassword123!",
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, test_user, auth_headers):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}

        response = await client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        """Test token refresh."""
        # First login to get tokens
        login_data = {
            "email": test_user["email"],
            "password": test_user["password"],
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()

        # Use refresh token
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test token refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}

        response = await client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_token(self, client: AsyncClient, auth_headers):
        """Test token verification endpoint."""
        response = await client.post("/api/v1/auth/verify-token", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user" in data

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers):
        """Test logout endpoint."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data.get("message", "").lower()


class TestOAuthEndpoints:
    """Test OAuth endpoints."""

    @pytest.mark.asyncio
    async def test_google_oauth_not_configured(self, client: AsyncClient):
        """Test Google OAuth when not configured."""
        # This test assumes GOOGLE_CLIENT_ID is not set
        response = await client.get("/api/v1/auth/google")

        # Should return 501 or 200 with auth_url depending on config
        assert response.status_code in [200, 501]
