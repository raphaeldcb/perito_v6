"""Pydantic schemas for dashboard alertas."""
from pydantic import BaseModel
from typing import Optional


class DashboardAlerta(BaseModel):
    """Alert data aggregated by type and status."""
    tipo: str
    status: str
    mensagem: str
    dias_vencimento: Optional[int] = None
    total_alertas: int

    class Config:
        from_attributes = True
