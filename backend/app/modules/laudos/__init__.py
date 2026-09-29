"""
Laudos module — Expertise report CRUD, generation, and download.

Wave 1 Modularization: Public interface (schemas + router only).
Internal implementation (models, repositories, services) isolated.

Exports:
- Schemas: LaudoSchema, LaudoCreateRequest, LaudoUpdateRequest, etc. (PUBLIC DTOs)
- Router: FastAPI APIRouter for integration into main.py

Never import models, repositories, or services from this module directly.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .schemas import (
    LaudoSchema,
    LaudoCreateRequest,
    LaudoUpdateRequest,
    LaudoStatusTransitionRequest,
    LaudoGenerateRequest,
    LaudoDownloadResponse,
    LaudoTemplateSchema,
    LaudoTemplateCreateRequest,
    LaudoListResponse,
)
from .routes import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "LaudoSchema",
    "LaudoCreateRequest",
    "LaudoUpdateRequest",
    "LaudoStatusTransitionRequest",
    "LaudoGenerateRequest",
    "LaudoDownloadResponse",
    "LaudoTemplateSchema",
    "LaudoTemplateCreateRequest",
    "LaudoListResponse",
    # Routes (PUBLIC — FastAPI integration)
    "router",
]
