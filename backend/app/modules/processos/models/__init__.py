"""Processo and Intimacao models for the processos module.

Note: Models are defined in app.models (process.py, kanban.py) and referenced here.
This module exports them for convenience within the processos module.
"""

from app.models.processo import Processo, TipoPericia, StatusProcesso
from app.models.kanban import Intimacao

__all__ = [
    "Processo",
    "TipoPericia",
    "StatusProcesso",
    "Intimacao",
]
