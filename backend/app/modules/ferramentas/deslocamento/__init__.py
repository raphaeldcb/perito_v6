"""
Deslocamento (travel distance/displacement) module.

Combines travel distance calculation (Google Maps), toll estimation (automatic + RotasBrasil API),
and flight comparison functionality into an isolated, reusable module.

Endpoints:
- POST /api/v1/deslocamento/calcular: Main calculation endpoint
- GET /api/v1/deslocamento/pedagio: Real-time toll calculation

Structure:
- router.py: FastAPI endpoints
- schemas.py: Pydantic request/response models
- service.py: Business logic (distance calculation, toll estimation, flight comparison)
"""

from .router import router

__all__ = ["router"]
