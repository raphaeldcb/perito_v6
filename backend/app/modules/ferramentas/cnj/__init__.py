"""
CNJ module — Conselho Nacional de Justiça (Brazilian Justice Council) number parsing and validation.

Isolated, stateless utility service with no external dependencies.
Pure Python regex-based CNJ number parsing.

All operations are deterministic and have p95 < 1ms.

Exports:
- Schemas: CNJRequest, CNJResponse, CNJParseResult (PUBLIC DTOs)
- Router: router (FastAPI integration)

Never import service directly — it's internal implementation.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .schemas import CNJRequest, CNJResponse, CNJParseResult
from .router import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "CNJRequest",
    "CNJResponse",
    "CNJParseResult",
    # Router (PUBLIC — FastAPI integration)
    "router",
]
