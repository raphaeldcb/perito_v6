"""Business logic for dashboard alertas."""
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models import LaudoAlerta
from .schemas import DashboardAlerta


def get_dashboard_alertas(db: Session) -> list[DashboardAlerta]:
    """
    Retrieve and aggregate alerts by type and status.

    Returns list of alerts grouped by tipo + status combination,
    including example alert data for each group.
    """
    alertas = db.query(LaudoAlerta).filter(LaudoAlerta.ativo == "sim").all()

    # Agrupa por tipo + status
    grupos = defaultdict(lambda: {"total": 0, "exemplo": None})
    for alerta in alertas:
        chave = f"{alerta.tipo}_{alerta.status}"
        grupos[chave]["total"] += 1
        if not grupos[chave]["exemplo"]:
            grupos[chave] = {
                "tipo": alerta.tipo,
                "status": alerta.status,
                "mensagem": alerta.mensagem or "",
                "dias_vencimento": alerta.dias_para_vencer,
                "total_alertas": 1
            }
        else:
            grupos[chave]["total_alertas"] += 1

    # Convert to list of DashboardAlerta objects
    return [DashboardAlerta(**v) for v in grupos.values()]
