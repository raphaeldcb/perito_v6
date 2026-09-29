"""Schemas Pydantic para API de Comunicações Judiciais."""

from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


class ComunicacaoConfigSchema(BaseModel):
    """Configuração de monitoramento de comunicações."""
    id: Optional[int] = None
    conta_email: str
    intervalo_minutos: int = 5
    ativo: bool = True
    ultima_execucao: Optional[datetime] = None
    proxima_execucao: Optional[datetime] = None

    class Config:
        from_attributes = True


class ComunicacaoDadosProcessuaisSchema(BaseModel):
    """Dados processuais extraídos de comunicação."""
    id: Optional[int] = None
    mensagem_id: int
    numero_processo: str
    vara: Optional[str] = None
    comarca: Optional[str] = None
    tribunal: Optional[str] = None

    class Config:
        from_attributes = True


class ComunicacaoMensagemListSchema(BaseModel):
    """Comunicação para listagem (resumida)."""
    id: int
    external_id: str
    remetente: str
    assunto: str
    data_recebimento: datetime
    eh_judicial: bool
    confianca_ia: Decimal
    status: str

    class Config:
        from_attributes = True


class ComunicacaoMensagemDetailSchema(BaseModel):
    """Comunicação detalhada."""
    id: int
    external_id: str
    remetente: str
    email_remetente: str
    assunto: str
    corpo: str
    data_recebimento: datetime
    eh_judicial: bool
    confianca_ia: Decimal
    status: str
    dados_processuais: Optional[ComunicacaoDadosProcessuaisSchema] = None

    class Config:
        from_attributes = True


class ComunicacaoLogSchema(BaseModel):
    """Log de operação de comunicações."""
    id: Optional[int] = None
    config_id: int
    operacao: str
    nivel: str
    mensagem: str
    dados: dict = {}
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExecutarMonitoramentoRequest(BaseModel):
    """Request para executar monitoramento."""
    conta_email: str = "financeiro@ipcms.com.br"
    limite: int = 50


class ExecutarMonitoramentoResponse(BaseModel):
    """Response da execução de monitoramento."""
    emails_processados: int
    emails_ignorados: int
    judiciais: int
    nao_judiciais: int
    erros: int


class PainelStatisticsSchema(BaseModel):
    """Estatísticas do painel."""
    total_mensagens: int
    judiciais_encontrados: int
    taxa_sucesso: float
    urgencia_breakdown: dict = {}
    ultima_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True
