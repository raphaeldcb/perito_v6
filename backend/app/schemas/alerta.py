from pydantic import BaseModel
from datetime import datetime


class AlertaRead(BaseModel):
    id: int
    laudo_id: int
    tipo: str
    status: str
    dias_para_vencer: int
    data_vencimento: datetime
    mensagem: str | None
    ativo: str

    class Config:
        from_attributes = True


class DashboardAlerta(BaseModel):
    tipo: str
    status: str
    mensagem: str
    dias_vencimento: int
    total_alertas: int
