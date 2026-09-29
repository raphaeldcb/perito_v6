from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class AnaliseForenseResultado(Base):
    __tablename__ = 'analise_forense_resultado'

    id = Column(String(36), primary_key=True)
    arquivo_hash_md5 = Column(String(32))
    arquivo_nome = Column(String(255))
    arquivo_tipo = Column(String(50))
    arquivo_tamanho_bytes = Column(Integer)
    resultado_json = Column(JSON)
    veredicto_final = Column(String(50))
    confianca_consenso = Column(Float)
    nivel_risco = Column(String(50))
    laudo_pdf_path = Column(String(255), nullable=True)
    laudo_json_path = Column(String(255), nullable=True)
    assinado = Column(Boolean, default=False)
    assinado_por = Column(String(255), nullable=True)
    timestamp_assinatura = Column(DateTime, nullable=True)
    certificado_a3_serial = Column(String(255), nullable=True)
    processo_id = Column(Integer, nullable=True)
    laudo_id = Column(Integer, nullable=True)
    timestamp_criacao = Column(DateTime, default=datetime.utcnow)
    timestamp_conclusao = Column(DateTime, nullable=True)
    tempo_total_ms = Column(Integer, nullable=True)
