from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
from .base import Base, TimestampMixin


class Laudo(Base, TimestampMixin):
    __tablename__ = "laudo"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False)
    tipo_laudo = Column(String(50), nullable=False)
    status = Column(String(50), default="rascunho")
    perito_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    revisor_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_emissao = Column(DateTime, nullable=True)
    data_assinatura = Column(DateTime, nullable=True)
    assinado_por = Column(String(200), nullable=True)
    arquivo_docx_path = Column(String(500), nullable=True)
    arquivo_pdf_path = Column(String(500), nullable=True)
    quesitos = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)

    versoes = relationship("LaudoVersao", back_populates="laudo", cascade="all, delete-orphan")
    auditorias = relationship("AuditoriaFable", back_populates="laudo", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_laudo_processo", "processo_id"),
        Index("idx_laudo_perito", "perito_id"),
        Index("idx_laudo_status", "status"),
    )


class LaudoVersao(Base, TimestampMixin):
    __tablename__ = "laudo_versao"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    numero_versao = Column(Integer, nullable=False)
    conteudo_markdown = Column(Text, nullable=False)
    gerado_por = Column(String(50), nullable=True)
    editado_por = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    laudo = relationship("Laudo", back_populates="versoes")

    __table_args__ = (
        Index("idx_laudo_versao_laudo", "laudo_id"),
    )


class AuditoriaFable(Base, TimestampMixin):
    __tablename__ = "auditoria_fable"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    versao_numero = Column(Integer, nullable=False)
    relatorio_json = Column(JSON, nullable=False)

    laudo = relationship("Laudo", back_populates="auditorias")

    __table_args__ = (
        Index("idx_auditoria_fable_laudo", "laudo_id"),
    )


# ===== PYDANTIC SCHEMAS FOR FAKE DETECTION API =====

class FakeDetectionResult(BaseModel):
    """Result object from fake detection analysis."""
    analyzed: bool = Field(..., description="Whether media was successfully analyzed")
    confidence: float = Field(..., description="Confidence score (0-100)")
    tags: List[str] = Field(default_factory=list, description="Detected fake indicators (e.g., 'deepfake', 'manipulated')")
    timestamp: str = Field(..., description="ISO 8601 timestamp when analysis was completed")

    class Config:
        json_schema_extra = {
            "example": {
                "analyzed": True,
                "confidence": 87.5,
                "tags": ["deepfake", "high_risk"],
                "timestamp": "2026-08-19T10:30:00Z"
            }
        }


class FakeDetectionJobResponse(BaseModel):
    """Response when submitting a fake detection job."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(default="queued", description="Current job status")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_12345",
                "status": "queued"
            }
        }


class FakeDetectionJobStatus(BaseModel):
    """Full job status including result (when done)."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status: queued, processing, done, failed")
    result: Optional[FakeDetectionResult] = Field(default=None, description="Analysis result when status=done")
    error: Optional[str] = Field(default=None, description="Error message when status=failed")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_12345",
                "status": "done",
                "result": {
                    "analyzed": True,
                    "confidence": 87.5,
                    "tags": ["deepfake"],
                    "timestamp": "2026-08-19T10:30:00Z"
                },
                "error": None
            }
        }
