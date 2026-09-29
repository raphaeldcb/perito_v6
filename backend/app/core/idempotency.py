"""
Idempotency management for event processing.

Prevents duplicate event processing by:
1. Storing processed idempotency keys in Redis
2. Checking before processing
3. TTL expiration (7 days default)

Ensures at-most-once semantics for event handlers.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # Redis is optional

from app.config.settings import settings

logger = logging.getLogger(__name__)


class IdempotencyKey:
    """
    Represents a unique idempotency key for event processing.

    Attributes:
        key: Unique identifier (e.g., "processo-1-created")
        ttl_seconds: Time-to-live in seconds (default: 7 days)
        created_at: When the key was created
    """

    def __init__(self, key: str, ttl_seconds: int = 7 * 24 * 60 * 60):
        """
        Initialize idempotency key.

        Args:
            key: Unique identifier
            ttl_seconds: TTL in seconds (default 7 days = 604800)
        """
        self.key = key
        self.ttl_seconds = ttl_seconds
        self.created_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if key has expired based on TTL."""
        expiration_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiration_time

    def __eq__(self, other):
        if isinstance(other, IdempotencyKey):
            return self.key == other.key
        return self.key == other

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        return f"IdempotencyKey(key='{self.key}', ttl={self.ttl_seconds}s)"


class IdempotencyStorage:
    """
    Manages idempotency key storage using Redis.

    Handles:
    - Marking events as processed
    - Checking if event was already processed
    - TTL expiration
    - Fallback to in-memory storage (development)
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize IdempotencyStorage.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or settings.__dict__.get(
            "redis_url", "redis://localhost:6379/0"
        )
        self.redis: Optional[aioredis.Redis] = None
        self._memory_store = {}  # Fallback for development
        self.processed_prefix = "idempotency"

    async def initialize(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url, encoding="utf8", decode_responses=True
            )
            await self.redis.ping()
            logger.info("IdempotencyStorage connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for idempotency: {e}")
            self.redis = None

    async def cleanup(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("IdempotencyStorage disconnected from Redis")

    async def mark_processed(self, idempotency_key: IdempotencyKey) -> bool:
        """
        Mark a key as processed.

        Args:
            idempotency_key: IdempotencyKey instance

        Returns:
            bool: True if newly marked, False if already processed
        """
        redis_key = f"{self.processed_prefix}:{idempotency_key.key}"

        try:
            if self.redis:
                # Use SET with NX (only set if not exists) — atomic
                result = await self.redis.set(
                    redis_key,
                    "1",
                    ex=idempotency_key.ttl_seconds,
                    nx=True,  # Only set if not exists
                )
                return result is True or result == b"OK" or result == "OK"
            else:
                # Fallback: in-memory
                if idempotency_key.key in self._memory_store:
                    return False
                self._memory_store[idempotency_key.key] = (
                    datetime.utcnow(),
                    idempotency_key.ttl_seconds,
                )
                return True

        except Exception as e:
            logger.error(f"Error marking idempotency key as processed: {e}")
            return False

    async def is_processed(self, key: str) -> bool:
        """
        Check if a key was already processed.

        Args:
            key: Idempotency key string

        Returns:
            bool: True if already processed
        """
        redis_key = f"{self.processed_prefix}:{key}"

        try:
            if self.redis:
                exists = await self.redis.exists(redis_key)
                return exists == 1
            else:
                # Fallback: check memory store and TTL
                if key in self._memory_store:
                    created_at, ttl_seconds = self._memory_store[key]
                    expiration_time = created_at + timedelta(seconds=ttl_seconds)
                    if datetime.utcnow() <= expiration_time:
                        return True
                    else:
                        # Remove expired entry
                        del self._memory_store[key]
                return False

        except Exception as e:
            logger.error(f"Error checking idempotency key: {e}")
            return False

    async def cleanup_expired(self):
        """
        Clean up expired idempotency keys (for Wave 3/maintenance).

        Redis does this automatically with expiration,
        this is for manual cleanup of in-memory store.
        """
        expired_keys = []

        for key, (created_at, ttl_seconds) in self._memory_store.items():
            expiration_time = created_at + timedelta(seconds=ttl_seconds)
            if datetime.utcnow() > expiration_time:
                expired_keys.append(key)

        for key in expired_keys:
            del self._memory_store[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired idempotency keys")

    async def get_stats(self) -> dict:
        """Get idempotency storage statistics (for monitoring)."""
        try:
            if self.redis:
                # Count keys with the processed prefix
                cursor = 0
                count = 0
                pattern = f"{self.processed_prefix}:*"

                while True:
                    cursor, keys = await self.redis.scan(
                        cursor, match=pattern, count=100
                    )
                    count += len(keys)
                    if cursor == 0:
                        break

                return {"type": "redis", "processed_keys": count}
            else:
                return {"type": "memory", "processed_keys": len(self._memory_store)}

        except Exception as e:
            logger.error(f"Error getting idempotency stats: {e}")
            return {"type": "unknown", "error": str(e)}
