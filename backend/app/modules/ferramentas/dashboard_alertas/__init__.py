"""Dashboard Alertas — aggregates laudo alerts by type and status."""
from .router import router
from .schemas import DashboardAlerta

__all__ = ["router", "DashboardAlerta"]
