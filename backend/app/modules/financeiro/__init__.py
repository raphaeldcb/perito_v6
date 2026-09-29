"""
Financeiro module — Payment management and financial operations.

Wave 1 Modularization: Public interface (schemas + router only).
Internal implementation (models, repositories, services) isolated.

Handles:
- Boleto generation and tracking via Banco Inter
- Nota fiscal management
- Honorário calculation and payment tracking
- Conta Única payment synchronization

Exports:
- Schemas: BoletoCreate, BoletoResponse, etc. (PUBLIC DTOs)
- Router: FastAPI APIRouter for integration into main.py

Never import models, repositories, or services from this module directly.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .schemas import (
    BoletoCreate, BoletoUpdate, BoletoResponse,
    NotaCreate, NotaUpdate, NotaResponse,
    HonorarioCreate, HonorarioUpdate, HonorarioResponse,
)
from .routes import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "BoletoCreate", "BoletoUpdate", "BoletoResponse",
    "NotaCreate", "NotaUpdate", "NotaResponse",
    "HonorarioCreate", "HonorarioUpdate", "HonorarioResponse",
    # Routes (PUBLIC — FastAPI integration)
    "router",
]
