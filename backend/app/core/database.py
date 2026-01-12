"""
MongoDB database connection and client management using Motor.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB."""
        try:
            logger.info("Connecting to MongoDB...")
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]

            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB: {settings.MONGODB_DB_NAME}")

            # Create indexes
            await cls.create_indexes()

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client:
            logger.info("Closing MongoDB connection...")
            cls.client.close()
            logger.info("MongoDB connection closed")

    @classmethod
    async def create_indexes(cls):
        """Create database indexes for performance."""
        if cls.db is None:
            return

        try:
            # Users collection indexes
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("auth_provider_id")
            await cls.db.users.create_index("created_at")

            # Goals collection indexes
            await cls.db.goals.create_index([("user_id", 1), ("created_at", -1)])
            await cls.db.goals.create_index("user_id")
            await cls.db.goals.create_index("phase")

            # Meetings collection indexes
            await cls.db.meetings.create_index([("user_id", 1), ("scheduled_at", -1)])
            await cls.db.meetings.create_index("scheduled_at")
            await cls.db.meetings.create_index("status")

            # Chat messages collection indexes
            await cls.db.chat_messages.create_index([("user_id", 1), ("timestamp", -1)])
            await cls.db.chat_messages.create_index("meeting_id")

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.db is None:
            raise Exception("Database not initialized. Call connect_db() first.")
        return cls.db


# Global database instance getter
async def get_database() -> AsyncIOMotorDatabase:
    """Dependency for getting database in route handlers."""
    return Database.get_db()
