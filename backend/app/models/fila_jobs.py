from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum
from datetime import datetime
import enum
from app.models.base import Base

class JobStatus(str, enum.Enum):
    PENDENTE = "pendente"
    EXECUTANDO = "executando"
    COMPLETO = "completo"
    ERRO = "erro"

class FilaJob(Base):
    __tablename__ = "fila_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False)  # "processar_pdf", "analisar_qwen"
    fila_id = Column(Integer, nullable=False)  # fila_intimacoes.id
    payload = Column(JSON, default={})
    resultado = Column(JSON, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDENTE)
    erro_msg = Column(String(500), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    executado_em = Column(DateTime, nullable=True)
