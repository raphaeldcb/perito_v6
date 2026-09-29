# v6/backend/app/schemas/comunicacoes.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class EmailMessageSchema(BaseModel):
    """Representação de e-mail para API."""
    id: Optional[int] = None
    message_id: str
    from_address: str
    from_name: Optional[str] = None
    subject: str
    received_datetime: datetime

    # Judicial
    is_judicial: bool
    judicial_confidence: Optional[float] = None

    # Dados processuais
    tribunal: Optional[str] = None
    vara: Optional[str] = None
    comarca: Optional[str] = None
    numero_processo: Optional[str] = None
    pedido: Optional[str] = None
    prazo: Optional[str] = None

    status: str
    resposta_enviada: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    categories: Optional[str] = None

    class Config:
        from_attributes = True


class EmailPainelStatsSchema(BaseModel):
    """Stats para painel principal."""
    recebidos_hoje: int
    judiciais: int
    completos: int
    pendentes: int
    revisar: int
    respondidos: int
    erros: int


class EmailConfigSchema(BaseModel):
    """Configuração do módulo."""
    mailbox_email: str
    intervalo_minutos: int = 5
    ativo: bool = True
    ultima_execucao: Optional[datetime] = None
    proxima_execucao: Optional[datetime] = None
    modo_resposta: str = "rascunho"
    campos_obrigatorios: dict = Field(default_factory=lambda: {"tribunal": True, "vara": True, "numero_processo": True, "pedido": True})

    class Config:
        from_attributes = True


class EmailTemplateSchema(BaseModel):
    """Template de resposta."""
    id: Optional[int] = None
    nome: str
    assunto: str
    corpo: str
    ativo: bool = True
    padrao: bool = False

    class Config:
        from_attributes = True
