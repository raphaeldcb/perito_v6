"""Laudos module models."""

from .laudo import LaudoModular, LaudoTemplate, LaudoStatusEnum, LaudoTipoEnum

# Public alias (use Laudo in module interfaces, maps to LaudoModular internally)
Laudo = LaudoModular

__all__ = ["Laudo", "LaudoModular", "LaudoTemplate", "LaudoStatusEnum", "LaudoTipoEnum"]
