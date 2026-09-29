"""Fila de jobs para processamento assíncrono.

Trabalhos que exigem o Mac (Chrome + certificado digital para ESAJ, protocolo
no tribunal) entram aqui com status 'na_fila'. O agente no Mac (scripts/
mac_agent.py) faz polling, executa via pipeline v5.3 e reporta o resultado.
Nada é marcado como concluído sem confirmação real.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, ForeignKey
from app.models.types import JSONBType
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True)
    tipo = Column(String(50), nullable=False)  # 'esaj_download', 'protocolo', 'analise_ia'
    payload = Column(JSONBType, nullable=False, default=dict)  # ex: {"numero_cnj": "...", "tribunal": "TJMS"}
    status = Column(String(20), nullable=False, default="na_fila")  # na_fila, processando, concluido, erro, falhou
    resultado = Column(JSONBType)  # preenchido pelo executor (caminho do PDF, nº protocolo real, etc.)
    erro = Column(Text)
    tentativas = Column(Integer, nullable=False, default=0)
    # P0 eSAJ limit: ativado quando migração no VPS estiver sincronizada
    # tentativas_esaj = Column(Integer, nullable=False, default=0)  # RULE: limite 15 para eSAJ
    # max_tentativas_permitidas = Column(Integer, nullable=False, default=15)  # Configurável
    # bloqueado_pela_regra = Column(String(100), nullable=True)  # Se bloqueado: "ESAJ_MAX_TENTATIVAS", motivo
    executor = Column(String(100))  # identificação de quem pegou o job (ex: 'mac-agent')
    iniciado_em = Column(DateTime)
    concluido_em = Column(DateTime)
    last_heartbeat = Column(DateTime)  # Última vez que o executor reportou progresso

    # Workflow integration: optional FK to track job origin from workflow
    workflow_execution_id = Column(Integer, ForeignKey('workflow_execution.id', ondelete='SET NULL'), nullable=True)

    # Relationship to WorkflowExecution (lazy load to avoid circular imports)
    workflow_execution = relationship("WorkflowExecution", foreign_keys=[workflow_execution_id])

    __table_args__ = (
        Index("idx_job_status_tipo", "status", "tipo"),
        Index("idx_job_processando_heartbeat", "status", "last_heartbeat"),
        Index("idx_job_workflow_execution", "workflow_execution_id"),
    )
