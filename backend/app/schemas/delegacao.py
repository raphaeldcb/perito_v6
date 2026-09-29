from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class DelegacaoCreate(BaseModel):
    tipo: str
    analista_id: int
    prestador_id: int
    processo_id: int | None = None
    valor: Decimal
    prazo_dias: int
    descricao: str | None = None


class DelegacaoAceitar(BaseModel):
    pass


class DelegacaoRecusar(BaseModel):
    motivo_recusa: str


class DelegacaoRead(BaseModel):
    id: int
    tipo: str
    analista_id: int
    prestador_id: int
    processo_id: int | None
    valor: Decimal
    prazo_dias: int
    status: str
    descricao: str | None
    motivo_recusa: str | None
    data_aceito: datetime | None
    data_concluido: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
