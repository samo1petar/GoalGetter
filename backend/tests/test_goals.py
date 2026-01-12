"""
Tests for goals CRUD endpoints.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from tests.conftest import create_test_goal_data


class TestGoalsEndpoints:
    """Test goals CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_goal(self, client: AsyncClient, auth_headers):
        """Test creating a new goal."""
        goal_data = create_test_goal_data("My Test Goal")

        response = await client.post(
            "/api/v1/goals",
            json=goal_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == goal_data["title"]
        assert data["content"] == goal_data["content"]
        assert data["phase"] == goal_data["phase"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_goal_minimal(self, client: AsyncClient, auth_headers):
        """Test creating a goal with minimal data."""
        goal_data = {
            "title": "Minimal Goal",
        }

        response = await client.post(
            "/api/v1/goals",
            json=goal_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == goal_data["title"]
        # Should have default values
        assert data["phase"] in ["draft", None, ""]

    @pytest.mark.asyncio
    async def test_create_goal_unauthorized(self, client: AsyncClient):
        """Test creating a goal without authentication."""
        goal_data = create_test_goal_data()

        response = await client.post("/api/v1/goals", json=goal_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_goals(self, client: AsyncClient, auth_headers, test_goal):
        """Test listing user goals."""
        response = await client.get("/api/v1/goals", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        assert "total" in data
        assert "page" in data
        assert len(data["goals"]) >= 1

    @pytest.mark.asyncio
    async def test_list_goals_pagination(self, client: AsyncClient, auth_headers, test_db, test_user):
        """Test goal listing with pagination."""
        # Create multiple goals
        from bson import ObjectId
        for i in range(15):
            await test_db.goals.insert_one({
                "_id": ObjectId(),
                "user_id": ObjectId(test_user["id"]),
                "title": f"Goal {i}",
                "content": f"Content {i}",
                "phase": "draft",
                "template_type": "smart",
                "metadata": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })

        # Test first page
        response = await client.get(
            "/api/v1/goals?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 10
        assert data["total"] == 15
        assert data["total_pages"] == 2

        # Test second page
        response = await client.get(
            "/api/v1/goals?page=2&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 5

    @pytest.mark.asyncio
    async def test_list_goals_filter_by_phase(self, client: AsyncClient, auth_headers, test_goal):
        """Test filtering goals by phase."""
        response = await client.get(
            f"/api/v1/goals?phase={test_goal['phase']}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for goal in data["goals"]:
            assert goal["phase"] == test_goal["phase"]

    @pytest.mark.asyncio
    async def test_list_goals_search(self, client: AsyncClient, auth_headers, test_goal):
        """Test searching goals."""
        response = await client.get(
            f"/api/v1/goals?search={test_goal['title'][:4]}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) >= 1

    @pytest.mark.asyncio
    async def test_get_goal(self, client: AsyncClient, auth_headers, test_goal):
        """Test getting a specific goal."""
        response = await client.get(
            f"/api/v1/goals/{test_goal['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_goal["id"]
        assert data["title"] == test_goal["title"]

    @pytest.mark.asyncio
    async def test_get_goal_not_found(self, client: AsyncClient, auth_headers):
        """Test getting a non-existent goal."""
        fake_id = "507f1f77bcf86cd799439011"

        response = await client.get(
            f"/api/v1/goals/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_goal_unauthorized(self, client: AsyncClient, test_goal):
        """Test getting a goal without authentication."""
        response = await client.get(f"/api/v1/goals/{test_goal['id']}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_goal(self, client: AsyncClient, auth_headers, test_goal):
        """Test updating a goal."""
        update_data = {
            "title": "Updated Goal Title",
            "content": "Updated content",
        }

        response = await client.put(
            f"/api/v1/goals/{test_goal['id']}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]

    @pytest.mark.asyncio
    async def test_update_goal_phase(self, client: AsyncClient, auth_headers, test_goal):
        """Test updating goal phase."""
        phase_data = {"phase": "active"}

        response = await client.patch(
            f"/api/v1/goals/{test_goal['id']}/phase",
            json=phase_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "active"

    @pytest.mark.asyncio
    async def test_delete_goal(self, client: AsyncClient, auth_headers, test_goal):
        """Test deleting a goal."""
        response = await client.delete(
            f"/api/v1/goals/{test_goal['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify goal is deleted
        get_response = await client.get(
            f"/api/v1/goals/{test_goal['id']}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_goal_not_found(self, client: AsyncClient, auth_headers):
        """Test deleting a non-existent goal."""
        fake_id = "507f1f77bcf86cd799439011"

        response = await client.delete(
            f"/api/v1/goals/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_goal_statistics(self, client: AsyncClient, auth_headers, test_goal):
        """Test getting goal statistics."""
        response = await client.get(
            "/api/v1/goals/statistics",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data or "draft" in data  # Statistics fields


class TestGoalTemplates:
    """Test goal template endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers):
        """Test listing goal templates."""
        response = await client.get("/api/v1/templates", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "templates" in data

    @pytest.mark.asyncio
    async def test_get_smart_template(self, client: AsyncClient, auth_headers):
        """Test getting SMART template."""
        response = await client.get("/api/v1/templates/smart", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "smart" or data.get("template_type") == "smart"

    @pytest.mark.asyncio
    async def test_get_okr_template(self, client: AsyncClient, auth_headers):
        """Test getting OKR template."""
        response = await client.get("/api/v1/templates/okr", headers=auth_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_goal_from_template(self, client: AsyncClient, auth_headers):
        """Test creating a goal from template."""
        template_data = {
            "template_type": "smart",
            "title": "Goal from Template",
        }

        response = await client.post(
            "/api/v1/goals/from-template",
            json=template_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == template_data["title"]
        assert data["template_type"] == "smart"


class TestGoalExport:
    """Test goal export endpoints."""

    @pytest.mark.asyncio
    async def test_export_goal_pdf(self, client: AsyncClient, auth_headers, test_goal):
        """Test exporting goal as PDF."""
        response = await client.get(
            f"/api/v1/goals/{test_goal['id']}/export",
            headers=auth_headers,
        )

        # Either succeeds with PDF or fails gracefully if PDF disabled
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"
