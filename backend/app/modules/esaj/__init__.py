"""
ESAJ module — Electronic System of Justice (Consult/Download) integration.

Wave 1 Modularization: Public interface (schemas + router only).
Internal implementation (models, repositories, services) isolated.

Provides:
- Schemas: ConsultaRequest, ConsultaResponse, etc. (PUBLIC DTOs)
- Router: FastAPI APIRouter for ESAJ integration (PUBLIC)

Never import models, repositories, or services from this module directly.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .routes.api import esaj_router as router

__all__ = [
    # Routes (PUBLIC — FastAPI integration)
    "router",
]
