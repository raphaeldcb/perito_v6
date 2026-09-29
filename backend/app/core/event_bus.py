"""
Event Bus infrastructure for async module communication via Redis Pub/Sub.

Provides:
- EventBus: Singleton for publish/subscribe/consume
- Event: Base event class with idempotency tracking
- Async workers: Poll Redis queue, invoke handlers
- Error recovery: Exponential backoff retry logic (1s, 2s, 4s)
- Durability: Events stored 7 days in Redis
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List, Callable, Type
from uuid import uuid4
from dataclasses import dataclass, field, asdict

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # Redis is optional

from app.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """
    Base event class for all domain events.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event (e.g., 'ProcessoCreated')
        timestamp: When event was created
        module: Source module (e.g., 'processos', 'laudos')
        payload: Event data (subclass-specific)
        idempotency_key: Unique key for idempotency check
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    module: str = ""
    idempotency_key: Optional[str] = None

    def __post_init__(self):
        """Set event type from class name if not provided."""
        if not self.event_type:
            self.event_type = self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        event_dict = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "module": self.module or self._infer_module(),
            "idempotency_key": self.idempotency_key,
            "payload": self._get_payload(),
        }
        return event_dict

    def _get_payload(self) -> Dict[str, Any]:
        """Get payload data from subclass attributes."""
        payload = {}
        for key, value in self.__dict__.items():
            if key not in [
                "event_id",
                "event_type",
                "timestamp",
                "module",
                "idempotency_key",
            ]:
                if isinstance(value, datetime):
                    payload[key] = value.isoformat()
                else:
                    payload[key] = value
        return payload

    def _infer_module(self) -> str:
        """Infer module from event type."""
        event_map = {
            "ProcessoCreated": "processos",
            "ProcessoUpdated": "processos",
            "LaudoGenerated": "laudos",
            "LaudoPublished": "laudos",
            "BoletoSynced": "financeiro",
            "ReceitaRecorded": "financeiro",
            "IntimacaoReceived": "esaj",
            "IntimacaoBumped": "esaj",
            "AnalysisCompleted": "ia",
        }
        return event_map.get(self.event_type, "system")


class EventBus:
    """
    Central event bus for async module communication via Redis Pub/Sub.

    Handles:
    - Publishing events to Redis queue
    - Subscribing to event types
    - Consuming events with handlers
    - Idempotency checks
    - Error recovery with exponential backoff
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize EventBus.

        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.__dict__.get(
            "redis_url", "redis://localhost:6379/0"
        )
        self.redis: Optional[aioredis.Redis] = None
        self.handlers: Dict[str, List[Callable]] = {}
        self.queue_key = "event:queue"
        self.processed_key = "event:processed"
        self.dlq_key = "event:dlq"  # Dead letter queue (Wave 3)

    async def initialize(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url, encoding="utf8", decode_responses=True
            )
            await self.redis.ping()
            logger.info("EventBus connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to in-memory queue for development
            self.redis = None
            self._memory_queue: List[Dict[str, Any]] = []

    async def cleanup(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("EventBus disconnected from Redis")

    async def publish(
        self, event: Event, idempotency_key: Optional[str] = None
    ) -> str:
        """
        Publish event to Redis queue.

        Args:
            event: Event instance to publish
            idempotency_key: Optional custom idempotency key

        Returns:
            event_id: Unique event ID

        Raises:
            Exception: If Redis operation fails
        """
        if idempotency_key:
            event.idempotency_key = idempotency_key
        else:
            event.idempotency_key = f"{event.event_type}:{event.event_id}"

        event_data = event.to_dict()
        event_json = json.dumps(event_data, default=str)

        try:
            if self.redis:
                # Store in Redis FIFO queue (use RPUSH for FIFO)
                await self.redis.rpush(self.queue_key, event_json)
                # Set TTL: 7 days
                await self.redis.expire(self.queue_key, 7 * 24 * 60 * 60)
            else:
                # Fallback: in-memory queue
                self._memory_queue.append(event_data)

            logger.info(f"Event published: {event.event_type} (ID: {event.event_id})")
            return event.event_id

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of event to handle
            handler: Async callable handler function
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)
        logger.info(f"Handler subscribed to {event_type}")

    async def consume(self, poll_interval: float = 1.0, max_retries: int = 3):
        """
        Start consuming events from queue.

        Polls Redis queue continuously and invokes handlers.

        Args:
            poll_interval: Seconds to wait between polls
            max_retries: Max retries per event before DLQ
        """
        logger.info("EventBus consumer started")

        while True:
            try:
                # Poll queue (LPOP for FIFO)
                if self.redis:
                    event_json = await self.redis.lpop(self.queue_key)
                else:
                    # Fallback: pop from memory queue
                    event_json = self._memory_queue.pop(0) if self._memory_queue else None

                if event_json:
                    event_data = json.loads(
                        event_json if isinstance(event_json, str) else event_json
                    )
                    await self._process_event(event_data, max_retries)

                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info("EventBus consumer stopped")
                break
            except Exception as e:
                logger.error(f"Error in event consumer: {e}")
                await asyncio.sleep(poll_interval)

    async def _process_event(self, event_data: Dict[str, Any], max_retries: int):
        """
        Process a single event with handlers.

        Args:
            event_data: Event dictionary
            max_retries: Max retries before DLQ
        """
        event_type = event_data.get("event_type")
        idempotency_key = event_data.get("idempotency_key")
        event_id = event_data.get("event_id")

        # Check idempotency
        if idempotency_key and await self._is_processed(idempotency_key):
            logger.info(f"Event already processed (ID: {event_id}), skipping")
            return

        # Get handlers for this event type
        handlers = self.handlers.get(event_type, [])
        if not handlers:
            logger.warning(f"No handlers for event type: {event_type}")
            return

        # Invoke handlers with retry logic
        payload = event_data.get("payload", {})
        retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

        for handler in handlers:
            retries = 0
            while retries <= max_retries:
                try:
                    await handler(payload)
                    # Mark as processed
                    if idempotency_key:
                        await self._mark_processed(idempotency_key)
                    logger.info(
                        f"Event processed: {event_type} (ID: {event_id}) "
                        f"by {handler.__name__}"
                    )
                    break  # Success, move to next handler

                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        # Move to dead letter queue (Wave 3)
                        await self._send_to_dlq(event_data, str(e))
                        logger.error(
                            f"Event failed (ID: {event_id}), moved to DLQ: {e}"
                        )
                        break
                    else:
                        # Retry with backoff
                        delay = retry_delays[min(retries - 1, len(retry_delays) - 1)]
                        logger.warning(
                            f"Handler {handler.__name__} failed (attempt {retries}), "
                            f"retrying in {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)

    async def _is_processed(self, idempotency_key: str) -> bool:
        """Check if event was already processed."""
        try:
            if self.redis:
                result = await self.redis.get(f"{self.processed_key}:{idempotency_key}")
                return result is not None
            else:
                # Fallback
                return False
        except Exception as e:
            logger.error(f"Error checking idempotency: {e}")
            return False

    async def _mark_processed(self, idempotency_key: str):
        """Mark event as processed."""
        try:
            if self.redis:
                # Store with 7-day TTL
                await self.redis.setex(
                    f"{self.processed_key}:{idempotency_key}",
                    7 * 24 * 60 * 60,
                    "1",
                )
            logger.debug(f"Event marked as processed: {idempotency_key}")
        except Exception as e:
            logger.error(f"Error marking event as processed: {e}")

    async def _send_to_dlq(self, event_data: Dict[str, Any], error: str):
        """Send event to dead letter queue (Wave 3)."""
        try:
            dlq_entry = {
                "event": event_data,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
            dlq_json = json.dumps(dlq_entry)

            if self.redis:
                await self.redis.rpush(self.dlq_key, dlq_json)
                # Set TTL: 7 days
                await self.redis.expire(self.dlq_key, 7 * 24 * 60 * 60)

            logger.warning(f"Event sent to DLQ: {dlq_entry}")

        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")

    async def get_queue_length(self) -> int:
        """Get current queue length (for monitoring)."""
        if self.redis:
            return await self.redis.llen(self.queue_key)
        else:
            return len(self._memory_queue) if hasattr(self, "_memory_queue") else 0

    async def get_dlq_length(self) -> int:
        """Get dead letter queue length (Wave 3)."""
        if self.redis:
            return await self.redis.llen(self.dlq_key)
        return 0


# Singleton instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get or create EventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.initialize()
    return _event_bus
