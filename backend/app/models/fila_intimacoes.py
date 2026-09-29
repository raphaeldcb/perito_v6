from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.base import Base

class FilaStatus(str, enum.Enum):
    RECEBIDO = "recebido"
    PROCESSANDO = "processando"
    PRONTO = "pronto"
    ERRO = "erro"

class FilaIntimacao(Base):
    __tablename__ = "fila_intimacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    oficio_path = Column(String(500), nullable=True)
    status = Column(Enum(FilaStatus), default=FilaStatus.RECEBIDO)
    criado_em = Column(DateTime, default=datetime.utcnow)
    criado_por = Column(Integer, ForeignKey("user.id"), nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    laudo = relationship("Laudo", back_populates="fila_intimacoes")
