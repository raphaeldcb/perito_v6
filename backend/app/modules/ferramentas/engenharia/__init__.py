"""Engenharia module — isolated vistoria management tool.

Schema-driven field inspection with offline PWA support, PDF generation,
automatic Qwen-powered report generation, and digital signatures.

Specialized models (Rural, Benfeitorias, Insalubridade, Energisa) preserved
from legacy implementation.

Exports:
- Router for FastAPI integration
- Schemas for request/response validation
"""

from .router import router
from .schemas import (
    ModeloVistoriaResponse,
    ModeloVistoriaDetailResponse,
    ModeloVistoriaCreateRequest,
    ModeloVistoriaUpdateRequest,
    VistoriaResponse,
    VistoriaDetailResponse,
    VistoriaCreateRequest,
    VistoriaEnviarRequest,
    VistoriaFotoCreateRequest,
    LaudoVistoriaResponse,
)

__all__ = [
    "router",
    # Modelo schemas
    "ModeloVistoriaResponse",
    "ModeloVistoriaDetailResponse",
    "ModeloVistoriaCreateRequest",
    "ModeloVistoriaUpdateRequest",
    # Vistoria schemas
    "VistoriaResponse",
    "VistoriaDetailResponse",
    "VistoriaCreateRequest",
    "VistoriaEnviarRequest",
    "VistoriaFotoCreateRequest",
    "LaudoVistoriaResponse",
]
