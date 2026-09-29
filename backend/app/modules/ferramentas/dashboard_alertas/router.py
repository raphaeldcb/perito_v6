"""Dashboard Alertas router — aggregates alerts by type and status."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services import get_db
from app.middleware import get_current_user
from app.models import User

from .schemas import DashboardAlerta
from .service import get_dashboard_alertas

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/alertas", response_model=list[DashboardAlerta])
async def listar_alertas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna alertas de dashboard por tipo e cor."""
    return get_dashboard_alertas(db)
