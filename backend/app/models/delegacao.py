from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey, Index, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin
import enum


class DelegacaoStatus(str, enum.Enum):
    PENDENTE = "pendente"
    ACEITO = "aceito"
    RECUSADO = "recusado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"


class DelegacaoTipo(str, enum.Enum):
    LAUDO_SIMPLES = "laudo_simples"
    LAUDO_COMPLEXO = "laudo_complexo"
    REVISAO = "revisao"
    PARECER = "parecer"


class Delegacao(Base, TimestampMixin):
    __tablename__ = "delegacao"

    id = Column(Integer, primary_key=True)
    tipo = Column(String(50), nullable=False)  # ENUM DelegacaoTipo
    analista_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    prestador_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=True)
    valor = Column(Numeric(12, 2), nullable=False)
    prazo_dias = Column(Integer, nullable=False)
    status = Column(String(30), default="pendente")  # ENUM DelegacaoStatus
    motivo_recusa = Column(Text, nullable=True)
    descricao = Column(Text, nullable=True)
    data_aceito = Column(DateTime, nullable=True)
    data_concluido = Column(DateTime, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)

    analista = relationship("User", foreign_keys=[analista_id], backref="delegacoes_como_analista")
    prestador = relationship("User", foreign_keys=[prestador_id], backref="delegacoes_como_prestador")
    processo = relationship("Processo", backref="delegacoes")

    __table_args__ = (
        Index("idx_delegacao_analista", "analista_id"),
        Index("idx_delegacao_prestador", "prestador_id"),
        Index("idx_delegacao_status", "status"),
        Index("idx_delegacao_processo", "processo_id"),
    )
