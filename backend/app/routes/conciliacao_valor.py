"""DEPRECATED: Conciliação (moved to modules/ferramentas/conciliacao).

This module is kept for backward compatibility. All functionality has been moved to:
app.modules.ferramentas.conciliacao

Please update imports to use the new module location.
"""
from app.modules.ferramentas.conciliacao import router

__all__ = ["router"]
