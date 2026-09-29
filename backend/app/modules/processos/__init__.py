"""
Processos module — Case (processo) and notification (intimacao) management.

Wave 1 Modularization: Public interface (schemas + router only).
Internal implementation (models, repositories, services) isolated.

Exports:
- Schemas: ProcessoResponseSchema, IntimacaoResponseSchema, etc. (PUBLIC DTOs)
- Router: FastAPI APIRouter for integration into main.py

Never import models, repositories, or services from this module directly.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .schemas import (
    ProcessoCreateSchema,
    ProcessoUpdateSchema,
    ProcessoResponseSchema,
    ProcessoListSchema,
    IntimacaoCreateSchema,
    IntimacaoUpdateSchema,
    IntimacaoResponseSchema,
    IntimacaoListSchema,
)
from .routes import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "ProcessoCreateSchema",
    "ProcessoUpdateSchema",
    "ProcessoResponseSchema",
    "ProcessoListSchema",
    "IntimacaoCreateSchema",
    "IntimacaoUpdateSchema",
    "IntimacaoResponseSchema",
    "IntimacaoListSchema",
    # Routes (PUBLIC — FastAPI integration)
    "router",
]
