from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class LaudoAlerta(Base, TimestampMixin):
    __tablename__ = "laudo_alerta"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False)  # LAUDO, OFICIO
    status = Column(String(20), nullable=False)  # VERDE, AMARELO, VERMELHO
    dias_para_vencer = Column(Integer, nullable=False)
    data_vencimento = Column(DateTime, nullable=False)
    mensagem = Column(String(500), nullable=True)
    email_enviado = Column(DateTime, nullable=True)
    ativo = Column(String(5), default="sim")  # sim, nao

    laudo = relationship("Laudo", backref="alertas")

    __table_args__ = (
        Index("idx_alerta_laudo", "laudo_id"),
        Index("idx_alerta_status", "status"),
        Index("idx_alerta_tipo", "tipo"),
    )
