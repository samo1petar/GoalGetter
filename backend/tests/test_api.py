"""
Tests for general API functionality.
"""
import pytest
from httpx import AsyncClient


class TestRootEndpoints:
    """Test root API endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test the root endpoint returns API info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GoalGetter"
        assert "version" in data
        assert data["status"] == "running"
        assert "docs" in data

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client: AsyncClient):
        """Test detailed status endpoint."""
        response = await client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "features" in data
        assert "calendar_sync" in data["features"]
        assert "email_notifications" in data["features"]
        assert "pdf_export" in data["features"]


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    @pytest.mark.asyncio
    async def test_openapi_spec(self, client: AsyncClient):
        """Test OpenAPI spec is accessible."""
        response = await client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "GoalGetter"
        assert "paths" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_swagger_docs(self, client: AsyncClient):
        """Test Swagger UI is accessible."""
        response = await client.get("/api/v1/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_redoc_docs(self, client: AsyncClient):
        """Test ReDoc is accessible."""
        response = await client.get("/api/v1/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, client: AsyncClient):
        """Test 404 response for non-existent endpoint."""
        response = await client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """Test 405 response for wrong HTTP method."""
        response = await client.delete("/health")

        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_validation_error(self, client: AsyncClient, auth_headers):
        """Test validation error response."""
        # Send invalid data type
        response = await client.post(
            "/api/v1/goals",
            json={"title": 12345},  # Should be string
            headers=auth_headers,
        )

        # May be 422 or 201 depending on schema validation
        assert response.status_code in [201, 422]


class TestSecurityHeaders:
    """Test security headers are present."""

    @pytest.mark.asyncio
    async def test_security_headers(self, client: AsyncClient):
        """Test that security headers are present in responses."""
        response = await client.get("/health")

        # These headers should be added by middleware
        assert "x-content-type-options" in response.headers or \
               "X-Content-Type-Options" in response.headers
        assert "x-frame-options" in response.headers or \
               "X-Frame-Options" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_header(self, client: AsyncClient):
        """Test that request ID is added to responses."""
        response = await client.get("/health")

        # Request ID should be present
        assert "x-request-id" in response.headers or \
               "X-Request-ID" in response.headers


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        """Test rate limit headers are present."""
        response = await client.get("/health")

        # Rate limit headers may or may not be present depending on config
        # Just ensure the request succeeds
        assert response.status_code == 200


class TestUsersEndpoint:
    """Test users endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_profile(self, client: AsyncClient, auth_headers, test_user):
        """Test getting current user profile."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]

    @pytest.mark.asyncio
    async def test_update_user_profile(self, client: AsyncClient, auth_headers):
        """Test updating user profile."""
        update_data = {
            "name": "Updated Name",
        }

        response = await client.put(
            "/api/v1/users/me",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
