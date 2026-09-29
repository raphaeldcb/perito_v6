"""
DNA Module — Isolated DNA analysis tool.

Modularized with self-contained router, schemas, and service.

Exports:
- router: FastAPI router for DNA endpoints
- schemas: Public DTOs
"""

from .router import router
from . import schemas

__all__ = ["router", "schemas"]
