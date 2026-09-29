"""AssistProduction ↔ Financeiro: custo real do tempo ocioso por colaborador.

Fluxo:
1. Agente AssistProduction (device) reporta eventos brutos de atividade/ociosidade
   via POST /api/v1/produtividade/eventos (autenticado com X-Agent-Key, igual aos
   outros agentes do sistema — mac_agent, windows_agent).
2. Job noturno (app/workers/produtividade_scheduler.py) agrega os eventos do dia
   anterior por device_id, calcula custo_hora do colaborador vinculado
   (salário ou honorário mensal / 160h) e grava o resumo do dia em
   assistproduction_financeiro_summary.
3. GET /api/v1/produtividade/custos lê o resumo para o dashboard e para os
   alertas de WhatsApp (threshold configurável em Parametro).

Nada aqui infere dado — se o device não está vinculado a um usuário
(usuario.device_id), o evento fica com usuario_id nulo e não entra em
nenhum cálculo de custo (aparece só como "device não vinculado" no relatório).
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Numeric, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AssistProductionEvento(Base, TimestampMixin):
    """Evento bruto reportado pelo agente AssistProduction instalado no device
    do colaborador. Cada evento cobre um intervalo de tempo classificado como
    'ativo' (colaborador trabalhando) ou 'ocioso' (sem interação — teclado/mouse
    parado, tela bloqueada, etc.)."""

    __tablename__ = "assistproduction_evento"

    id = Column(Integer, primary_key=True)
    device_id = Column(String(100), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, nullable=False)  # início do intervalo (hora local do device, enviado em UTC)
    tipo = Column(String(20), nullable=False)  # 'ativo' | 'ocioso'
    duracao_segundos = Column(Integer, nullable=False, default=0)
    app_ativo = Column(String(200))  # janela/app em foco no momento (telemetria opcional)
    processado = Column(Boolean, nullable=False, default=False)  # já entrou em algum summary diário?

    usuario = relationship("User", foreign_keys=[usuario_id])

    __table_args__ = (
        Index("idx_assistprod_evento_device_ts", "device_id", "timestamp"),
        Index("idx_assistprod_evento_usuario_ts", "usuario_id", "timestamp"),
        Index("idx_assistprod_evento_processado", "processado"),
    )


class AssistProductionFinanceiroSummary(Base, TimestampMixin):
    """Resumo diário: quanto tempo o colaborador ficou ocioso e quanto isso
    custou, com base no custo_hora vigente na data do cálculo (salvo como
    snapshot — se o salário mudar depois, o histórico não se reescreve)."""

    __tablename__ = "assistproduction_financeiro_summary"

    id = Column(Integer, primary_key=True)
    device_id = Column(String(100), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data = Column(Date, nullable=False)

    tempo_ativo_segundos = Column(Integer, nullable=False, default=0)
    tempo_desperdicado_segundos = Column(Integer, nullable=False, default=0)  # ocioso

    custo_hora = Column(Numeric(10, 2))            # snapshot do custo_hora usado
    custo_desperdicado = Column(Numeric(12, 2), nullable=False, default=0)   # tempo_desperdicado_h * custo_hora

    alerta_enviado = Column(Boolean, nullable=False, default=False)
    alerta_enviado_em = Column(DateTime)

    usuario = relationship("User", foreign_keys=[usuario_id])

    __table_args__ = (
        Index("idx_assistprod_summary_device_data", "device_id", "data", unique=True),
        Index("idx_assistprod_summary_usuario_data", "usuario_id", "data"),
        Index("idx_assistprod_summary_data", "data"),
    )
