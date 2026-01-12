"""
Redis connection and client management.
"""
import redis.asyncio as redis
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client manager."""

    client: Optional[redis.Redis] = None

    @classmethod
    async def connect_redis(cls):
        """Connect to Redis."""
        try:
            logger.info("Connecting to Redis...")
            cls.client = await redis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await cls.client.ping()
            logger.info("Successfully connected to Redis")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    @classmethod
    async def close_redis(cls):
        """Close Redis connection."""
        if cls.client:
            logger.info("Closing Redis connection...")
            await cls.client.close()
            logger.info("Redis connection closed")

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get Redis client instance."""
        if not cls.client:
            raise Exception("Redis not initialized. Call connect_redis() first.")
        return cls.client

    @classmethod
    async def set_cache(cls, key: str, value: str, ttl: int = None):
        """Set a value in cache with optional TTL."""
        client = cls.get_client()
        if ttl:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)

    @classmethod
    async def get_cache(cls, key: str) -> Optional[str]:
        """Get a value from cache."""
        client = cls.get_client()
        return await client.get(key)

    @classmethod
    async def delete_cache(cls, key: str):
        """Delete a key from cache."""
        client = cls.get_client()
        await client.delete(key)

    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists in cache."""
        client = cls.get_client()
        return await client.exists(key) > 0


# Global Redis client getter
async def get_redis() -> redis.Redis:
    """Dependency for getting Redis client in route handlers."""
    return RedisClient.get_client()
