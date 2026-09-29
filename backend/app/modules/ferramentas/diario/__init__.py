"""
Diario Module (DJEN) — Diário Oficial Legal Journal Monitoring.

Isolated module for monitoring legal journals across Brazilian courts.
Provides configuration management, publication search, and opportunity scoring.

Exports:
- Schemas: ConfigInput, ConsultaInput, AnalisarInput (PUBLIC DTOs)
- Router: router (FastAPI integration)

All operations require authentication. Use app.shared DTOs for inter-module communication.
"""

from .schemas import ConfigInput, ConsultaInput, AnalisarInput
from .router import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "ConfigInput",
    "ConsultaInput",
    "AnalisarInput",
    # Router (PUBLIC — FastAPI integration)
    "router",
]
