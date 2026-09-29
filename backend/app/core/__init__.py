"""
Core module for Event Bus infrastructure (Wave 2 — Resiliência).

Provides:
- EventBus: Async pub/sub via Redis
- Event types: ProcessoCreated, LaudoGenerated, etc.
- Idempotency: Prevent duplicate processing (at-most-once semantics)
- Workers: event_consumer.py consumes and invokes handlers

Usage:
    from app.core import EventBus, ProcessoCreated

    bus = EventBus()
    await bus.initialize()

    # Publish
    event = ProcessoCreated(processo_id=1, numero="...", valor=50000.0)
    await bus.publish(event)

    # Subscribe
    async def handle_processo_created(payload):
        print(f"Processo created: {payload}")

    await bus.subscribe("ProcessoCreated", handle_processo_created)

    # Consume (usually runs in separate worker)
    asyncio.create_task(bus.consume())
"""

from .event_bus import EventBus, Event, get_event_bus
from .events import (
    ProcessoCreated,
    ProcessoUpdated,
    LaudoGenerated,
    LaudoPublished,
    BoletoSynced,
    ReceitaRecorded,
    IntimacaoReceived,
    IntimacaoBumped,
    AnalysisCompleted,
    EVENT_TYPE_MAP,
)
from .idempotency import IdempotencyKey, IdempotencyStorage

__all__ = [
    # EventBus
    "EventBus",
    "Event",
    "get_event_bus",
    # Events
    "ProcessoCreated",
    "ProcessoUpdated",
    "LaudoGenerated",
    "LaudoPublished",
    "BoletoSynced",
    "ReceitaRecorded",
    "IntimacaoReceived",
    "IntimacaoBumped",
    "AnalysisCompleted",
    "EVENT_TYPE_MAP",
    # Idempotency
    "IdempotencyKey",
    "IdempotencyStorage",
]
