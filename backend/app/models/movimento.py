"""Movimentos financeiros por processo — despesas e entradas de cada perícia.

Faz o sistema "conhecer a empresa em números": cada processo acumula custos
(deslocamento, vistoria, custas...) e entradas, e o sistema calcula o custo
real até o recebimento (corrigido por IPCA).
"""
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class MovimentoProcesso(Base, TimestampMixin):
    __tablename__ = "movimento_processo"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(10), nullable=False)   # despesa | entrada
    categoria = Column(String(40))               # deslocamento, vistoria, custas, honorário, outro
    descricao = Column(String(200))
    valor = Column(Numeric(12, 2), nullable=False)
    data = Column(Date)

    processo = relationship("Processo")

    __table_args__ = (
        Index("idx_mov_processo", "processo_id"),
    )
