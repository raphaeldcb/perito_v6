"""Forensic analysis models."""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean
from datetime import datetime
from .base import Base, TimestampMixin


class ForensicAnalysis(Base, TimestampMixin):
    """Forensic analysis record with laudo generation URLs."""

    __tablename__ = "forensic_analysis"

    id = Column(Integer, primary_key=True)

    # File information
    arquivo_nome = Column(String(255), nullable=True, comment="Nome original do arquivo")
    arquivo_tipo = Column(String(50), nullable=True, comment="Tipo MIME do arquivo")
    arquivo_tamanho_bytes = Column(Integer, nullable=True, comment="Tamanho em bytes")
    arquivo_hash_md5 = Column(String(32), nullable=True, comment="Hash MD5 do arquivo")

    # Analysis results
    resultado_json = Column(JSON, nullable=True, comment="Resultado completo da análise em JSON")
    veredicto_final = Column(String(50), nullable=True, comment="Veredicto final")
    confianca_consenso = Column(Float, nullable=True, comment="Score de confiança (0.0-1.0)")
    nivel_risco = Column(String(50), nullable=True, comment="Nível de risco")

    # Laudo URLs (generated files on OneDrive)
    laudo_docx_url = Column(String(500), nullable=True, comment="URL do laudo DOCX no OneDrive")
    laudo_pdf_url = Column(String(500), nullable=True, comment="URL do laudo PDF no OneDrive")
    laudo_generated_at = Column(DateTime, nullable=True, comment="Data de geração do laudo")

    # Timestamps
    timestamp_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    timestamp_conclusao = Column(DateTime, nullable=True, comment="Data de conclusão da análise")
