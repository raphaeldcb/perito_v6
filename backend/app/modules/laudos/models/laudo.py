"""
Laudos module models — Laudo and LaudoTemplate SQLAlchemy ORM entities.

Status transitions: RASCUNHO → REVISION → ASSINADO → ARQUIVADO
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from app.models.base import Base, TimestampMixin


class LaudoStatusEnum(str, PyEnum):
    """Laudo status state machine."""
    RASCUNHO = "rascunho"
    REVISION = "revision"
    ASSINADO = "assinado"
    ARQUIVADO = "arquivado"


class LaudoTipoEnum(str, PyEnum):
    """Laudo type classification."""
    JUDICIAL = "judicial"
    EXTRAJUDICIAL = "extrajudicial"


class LaudoModular(Base, TimestampMixin):
    """
    Laudo (expertise report) entity — modular Wave 1 version.

    Links to processo (case), perito (expert), and template.
    Supports DOCX generation and PDF export.

    Note: Class named LaudoModular to avoid conflict with monolithic Laudo model.
    Database table: laudos_v2 (migration will consolidate to 'laudo' in Wave 2).
    """
    __tablename__ = "laudos_v2"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(50), unique=True, nullable=False, index=True)
    processo_id = Column(Integer, ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(Enum(LaudoTipoEnum), nullable=False)
    status = Column(Enum(LaudoStatusEnum), default=LaudoStatusEnum.RASCUNHO, nullable=False, index=True)

    # Content: JSON blob with analysis data from IA
    conteudo = Column(JSON, nullable=True)

    # Template reference
    template_id = Column(Integer, ForeignKey("laudo_templates.id"), nullable=True)

    # File storage paths (local /tmp Wave 1, S3 Wave 2)
    arquivo_docx_path = Column(String(500), nullable=True)
    arquivo_pdf_path = Column(String(500), nullable=True)

    # Signature
    assinante_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    data_assinatura = Column(DateTime, nullable=True)

    # Metadata
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_emissao = Column(DateTime, nullable=True)

    # Soft delete
    deletado = Column(Boolean, default=False, nullable=False)
    deletado_em = Column(DateTime, nullable=True)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    # Relationships
    template = relationship("LaudoTemplate", back_populates="laudos_modular")
    # assinante and deletado_por relationships omitted (no Usuario model in this module)
    # They will be resolved at ORM level when Usuario is imported

    __table_args__ = (
        Index("idx_laudos_v2_processo_id", "processo_id"),
        Index("idx_laudos_v2_status", "status"),
        Index("idx_laudos_v2_numero", "numero"),
        Index("idx_laudos_v2_deletado", "deletado"),
    )


class LaudoTemplate(Base, TimestampMixin):
    """
    Laudo template for DOCX generation.

    Stores template placeholders: {analise}, {conclusao}, {assinatura}.
    Wave 1: hardcoded 2-3 templates. UI editing deferred to Wave 2.
    """
    __tablename__ = "laudo_templates"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False, index=True)
    tipo = Column(Enum(LaudoTipoEnum), nullable=False)
    conteudo = Column(Text, nullable=False)  # Template with placeholders
    descricao = Column(String(500), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    laudos_modular = relationship("LaudoModular", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_templates_v2_nome", "nome"),
        Index("idx_templates_v2_ativo", "ativo"),
    )
