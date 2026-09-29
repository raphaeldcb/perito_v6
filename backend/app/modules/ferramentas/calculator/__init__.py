"""
Calculator module — Deslocamento (travel expenses) and juros (interest) calculations.

Isolated, stateless utility service with no external dependencies.
Pure Python financial calculations.

All operations are deterministic and have p95 < 1ms.

Exports:
- Schemas: DeslocamentoRequest, DeslocamentoResponse, JurosRequest, JurosResponse (PUBLIC DTOs)
- Router: router (FastAPI integration)

Never import service directly — it's internal implementation.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .schemas import (
    DeslocamentoRequest,
    DeslocamentoResponse,
    JurosRequest,
    JurosResponse,
    CalculatorResponse,
)
from .router import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "DeslocamentoRequest",
    "DeslocamentoResponse",
    "JurosRequest",
    "JurosResponse",
    "CalculatorResponse",
    # Router (PUBLIC — FastAPI integration)
    "router",
]
