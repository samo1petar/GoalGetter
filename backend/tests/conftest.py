"""
Pytest configuration and fixtures for GoalGetter tests.
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

# Set test environment before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-at-least-32-chars"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/goalgetter_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

from app.main import app
from app.core.database import Database
from app.core.redis import RedisClient
from app.core.security import SecurityUtils
from app.models.user import UserModel


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Create a test database connection."""
    # Connect to test database
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.goalgetter_test

    # Clean up collections before each test
    collections = await db.list_collection_names()
    for collection in collections:
        await db[collection].delete_many({})

    yield db

    # Cleanup after test
    for collection in collections:
        await db[collection].delete_many({})

    client.close()


@pytest_asyncio.fixture(scope="function")
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked database."""
    # Mock database
    Database._db = test_db

    # Mock Redis (optional for tests)
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)
    mock_redis.ping = AsyncMock(return_value=True)
    RedisClient._redis = mock_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(test_db) -> Dict[str, Any]:
    """Create a test user in the database."""
    user_data = {
        "_id": ObjectId(),
        "email": "test@example.com",
        "name": "Test User",
        "auth_provider": "email",
        "auth_provider_id": "test@example.com",
        "hashed_password": SecurityUtils.get_password_hash("TestPassword123!"),
        "phase": "goal_setting",
        "meeting_interval_days": 7,
        "profile_image": None,
        "preferences": {
            "timezone": "UTC",
            "email_notifications": True,
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await test_db.users.insert_one(user_data)

    return {
        "id": str(user_data["_id"]),
        "email": user_data["email"],
        "name": user_data["name"],
        "phase": user_data["phase"],
        "password": "TestPassword123!",
    }


@pytest_asyncio.fixture
async def auth_headers(test_user) -> Dict[str, str]:
    """Create authentication headers with valid JWT token."""
    token = SecurityUtils.create_access_token({
        "user_id": test_user["id"],
        "email": test_user["email"],
    })
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_goal(test_db, test_user) -> Dict[str, Any]:
    """Create a test goal in the database."""
    goal_data = {
        "_id": ObjectId(),
        "user_id": ObjectId(test_user["id"]),
        "title": "Test Goal",
        "content": "This is a test goal content.",
        "phase": "draft",
        "template_type": "smart",
        "metadata": {
            "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "milestones": ["Milestone 1", "Milestone 2"],
            "tags": ["test", "development"],
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await test_db.goals.insert_one(goal_data)

    return {
        "id": str(goal_data["_id"]),
        "user_id": test_user["id"],
        "title": goal_data["title"],
        "content": goal_data["content"],
        "phase": goal_data["phase"],
        "template_type": goal_data["template_type"],
    }


@pytest_asyncio.fixture
async def test_meeting(test_db, test_user) -> Dict[str, Any]:
    """Create a test meeting in the database."""
    meeting_time = datetime.utcnow() + timedelta(hours=1)
    meeting_data = {
        "_id": ObjectId(),
        "user_id": ObjectId(test_user["id"]),
        "scheduled_at": meeting_time,
        "duration_minutes": 30,
        "status": "scheduled",
        "calendar_event_id": None,
        "notes": "Test meeting notes",
        "created_at": datetime.utcnow(),
        "completed_at": None,
    }

    await test_db.meetings.insert_one(meeting_data)

    return {
        "id": str(meeting_data["_id"]),
        "user_id": test_user["id"],
        "scheduled_at": meeting_time.isoformat(),
        "duration_minutes": meeting_data["duration_minutes"],
        "status": meeting_data["status"],
    }


# Helper functions for tests
def create_test_user_data(email: str = "newuser@example.com") -> Dict[str, str]:
    """Create user registration data for tests."""
    return {
        "email": email,
        "name": "New Test User",
        "password": "NewPassword123!",
    }


def create_test_goal_data(title: str = "New Goal") -> Dict[str, Any]:
    """Create goal data for tests."""
    return {
        "title": title,
        "content": "Goal content for testing",
        "phase": "draft",
        "template_type": "smart",
        "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
        "milestones": ["Step 1", "Step 2"],
        "tags": ["test"],
    }
