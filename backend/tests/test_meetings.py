"""
Tests for meeting endpoints.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


class TestMeetingsEndpoints:
    """Test meeting CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_meeting(self, client: AsyncClient, auth_headers):
        """Test creating a new meeting."""
        meeting_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        meeting_data = {
            "scheduled_at": meeting_time,
            "duration_minutes": 30,
            "notes": "Initial meeting notes",
        }

        response = await client.post(
            "/api/v1/meetings",
            json=meeting_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["duration_minutes"] == 30
        assert data["status"] == "scheduled"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_setup_meetings(self, client: AsyncClient, auth_headers):
        """Test setting up recurring meetings."""
        setup_data = {
            "interval_days": 7,
            "duration_minutes": 30,
            "preferred_hour": 10,
            "preferred_minute": 0,
        }

        response = await client.post(
            "/api/v1/meetings/setup",
            json=setup_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["duration_minutes"] == 30
        assert data["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_list_meetings(self, client: AsyncClient, auth_headers, test_meeting):
        """Test listing meetings."""
        response = await client.get("/api/v1/meetings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "meetings" in data
        assert "total" in data
        assert len(data["meetings"]) >= 1

    @pytest.mark.asyncio
    async def test_list_meetings_upcoming_only(self, client: AsyncClient, auth_headers, test_meeting):
        """Test listing only upcoming meetings."""
        response = await client.get(
            "/api/v1/meetings?upcoming_only=true",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # All meetings should be in the future
        now = datetime.utcnow()
        for meeting in data["meetings"]:
            meeting_time = datetime.fromisoformat(meeting["scheduled_at"].replace("Z", "+00:00"))
            # Allow some margin for test execution
            assert meeting_time >= now - timedelta(minutes=5)

    @pytest.mark.asyncio
    async def test_list_meetings_filter_by_status(
        self, client: AsyncClient, auth_headers, test_meeting
    ):
        """Test filtering meetings by status."""
        response = await client.get(
            "/api/v1/meetings?status=scheduled",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for meeting in data["meetings"]:
            assert meeting["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_get_meeting(self, client: AsyncClient, auth_headers, test_meeting):
        """Test getting a specific meeting."""
        response = await client.get(
            f"/api/v1/meetings/{test_meeting['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_meeting["id"]
        assert data["duration_minutes"] == test_meeting["duration_minutes"]

    @pytest.mark.asyncio
    async def test_get_meeting_not_found(self, client: AsyncClient, auth_headers):
        """Test getting a non-existent meeting."""
        fake_id = "507f1f77bcf86cd799439011"

        response = await client.get(
            f"/api/v1/meetings/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_next_meeting(self, client: AsyncClient, auth_headers, test_meeting):
        """Test getting the next scheduled meeting."""
        response = await client.get("/api/v1/meetings/next", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # May or may not have a meeting depending on test state
        if data.get("meeting"):
            assert "scheduled_at" in data["meeting"]

    @pytest.mark.asyncio
    async def test_update_meeting(self, client: AsyncClient, auth_headers, test_meeting):
        """Test updating a meeting."""
        update_data = {
            "duration_minutes": 45,
            "notes": "Updated meeting notes",
        }

        response = await client.put(
            f"/api/v1/meetings/{test_meeting['id']}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["duration_minutes"] == 45
        assert data["notes"] == "Updated meeting notes"

    @pytest.mark.asyncio
    async def test_reschedule_meeting(self, client: AsyncClient, auth_headers, test_meeting):
        """Test rescheduling a meeting."""
        new_time = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"
        reschedule_data = {
            "scheduled_at": new_time,
            "notes": "Rescheduled due to conflict",
        }

        response = await client.put(
            f"/api/v1/meetings/{test_meeting['id']}/reschedule",
            json=reschedule_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Time should be updated
        assert data["notes"] == "Rescheduled due to conflict" or \
               "rescheduled" in data.get("notes", "").lower()

    @pytest.mark.asyncio
    async def test_cancel_meeting(self, client: AsyncClient, auth_headers, test_meeting):
        """Test cancelling a meeting."""
        response = await client.delete(
            f"/api/v1/meetings/{test_meeting['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify meeting is cancelled
        get_response = await client.get(
            f"/api/v1/meetings/{test_meeting['id']}",
            headers=auth_headers,
        )

        # Should be deleted or marked as cancelled
        assert get_response.status_code in [200, 404]
        if get_response.status_code == 200:
            assert get_response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_complete_meeting(self, client: AsyncClient, auth_headers, test_db, test_meeting):
        """Test completing a meeting."""
        from bson import ObjectId

        # First, make the meeting active
        await test_db.meetings.update_one(
            {"_id": ObjectId(test_meeting["id"])},
            {"$set": {"status": "active"}},
        )

        complete_data = {"notes": "Great session! Made progress on goals."}

        response = await client.post(
            f"/api/v1/meetings/{test_meeting['id']}/complete",
            json=complete_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_check_meeting_access(self, client: AsyncClient, auth_headers):
        """Test checking meeting access."""
        response = await client.get("/api/v1/meetings/access", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "can_access" in data
        assert "user_phase" in data

    @pytest.mark.asyncio
    async def test_get_calendar_status(self, client: AsyncClient, auth_headers):
        """Test getting calendar integration status."""
        response = await client.get("/api/v1/meetings/calendar/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data or "available" in data or "configured" in data
