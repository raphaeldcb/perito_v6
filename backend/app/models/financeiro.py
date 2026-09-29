"""Conciliação bancária: extrato mensal → lançamentos → match com coletador/usuário.

Fluxo: admin lança o extrato do banco (CSV/OFX). Cada lançamento de saída é
casado automaticamente pelo nome do favorecido com um coletador (apelido/nome)
ou usuário. Ao casar, o comprovante daquele lançamento fica vinculado ao
conveniado/prestador. Casamento manual sempre disponível (Bruno e alguns
recebem por outras formas).
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ExtratoBancario(Base, TimestampMixin):
    __tablename__ = "extrato_bancario"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    banco = Column(String(120))
    competencia = Column(String(7))  # "2026-07"
    arquivo_path = Column(String(500))
    total_lancamentos = Column(Integer, default=0)
    total_conciliados = Column(Integer, default=0)

    lancamentos = relationship("LancamentoBancario", back_populates="extrato", cascade="all, delete-orphan")


class LancamentoBancario(Base, TimestampMixin):
    __tablename__ = "lancamento_bancario"

    id = Column(Integer, primary_key=True)
    extrato_id = Column(Integer, ForeignKey("extrato_bancario.id", ondelete="CASCADE"), nullable=False)
    data = Column(Date)
    descricao = Column(Text)              # texto bruto do extrato (favorecido, histórico)
    favorecido = Column(String(200))      # nome extraído para o match
    valor = Column(Numeric(12, 2))
    tipo = Column(String(10))             # credito | debito

    # Resultado da conciliação
    status = Column(String(20), default="pendente")  # pendente, conciliado, ignorado
    coletador_id = Column(Integer, ForeignKey("coletador.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    match_score = Column(Numeric(4, 3))   # confiança do match automático (0-1)
    match_manual = Column(Boolean, default=False)
    comprovante_id = Column(Integer, ForeignKey("documento_coletador.id"), nullable=True)

    # Soft-delete
    ativo = Column(Boolean, default=True, nullable=False)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)

    extrato = relationship("ExtratoBancario", back_populates="lancamentos")

    __table_args__ = (
        Index("idx_lancamento_status", "status"),
        Index("idx_lancamento_favorecido", "favorecido"),
    )
