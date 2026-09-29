"""
Laudos module schemas — Request/response DTOs.

All responses wrapped in ApiResponse (shared layer).
Interfaces for CRUD, generation, and download operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum


class LaudoStatusEnum(str, Enum):
    """Laudo status."""
    RASCUNHO = "rascunho"
    REVISION = "revision"
    ASSINADO = "assinado"
    ARQUIVADO = "arquivado"


class LaudoTipoEnum(str, Enum):
    """Laudo type."""
    JUDICIAL = "judicial"
    EXTRAJUDICIAL = "extrajudicial"


class LaudoSchema(BaseModel):
    """LA-00: Laudo DTO (read)."""

    id: int
    numero: str
    processo_id: int
    tipo: LaudoTipoEnum
    status: LaudoStatusEnum
    conteudo: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    arquivo_docx_path: Optional[str] = None
    arquivo_pdf_path: Optional[str] = None
    assinante_id: Optional[int] = None
    data_assinatura: Optional[datetime] = None
    data_criacao: datetime
    data_emissao: Optional[datetime] = None
    deletado: bool = False
    deletado_em: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LaudoCreateRequest(BaseModel):
    """LA-01: Create laudo request."""

    numero: str = Field(..., min_length=1, max_length=50, description="Laudo number (unique)")
    processo_id: int = Field(..., description="FK to processo")
    tipo: LaudoTipoEnum = Field(..., description="Laudo type")
    template_id: Optional[int] = Field(None, description="FK to template")
    conteudo: Optional[Dict[str, Any]] = Field(None, description="Initial content (JSON)")


class LaudoUpdateRequest(BaseModel):
    """LA-02: Update laudo request."""

    numero: Optional[str] = None
    tipo: Optional[LaudoTipoEnum] = None
    template_id: Optional[int] = None
    conteudo: Optional[Dict[str, Any]] = None


class LaudoStatusTransitionRequest(BaseModel):
    """LA-03: Status transition request."""

    new_status: LaudoStatusEnum = Field(..., description="Target status")
    motivo: Optional[str] = Field(None, description="Reason for transition")


class LaudoGenerateRequest(BaseModel):
    """LA-04: Generate DOCX request."""

    template_id: Optional[int] = Field(None, description="Override template (use default if None)")
    conteudo: Optional[Dict[str, Any]] = Field(None, description="Override content (use existing if None)")


class LaudoDownloadResponse(BaseModel):
    """LA-05: Download DOCX/PDF response metadata."""

    laudo_id: int
    arquivo_path: str
    formato: str = Field(..., description="docx | pdf")
    tamanho_bytes: int
    data_criacao: datetime


class LaudoTemplateSchema(BaseModel):
    """LA-09: Laudo template DTO (read)."""

    id: int
    nome: str
    tipo: LaudoTipoEnum
    descricao: Optional[str] = None
    ativo: bool
    conteudo: Optional[str] = None  # May be omitted in list response
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LaudoTemplateCreateRequest(BaseModel):
    """LA-08: Create laudo template request."""

    nome: str = Field(..., min_length=1, max_length=100, description="Template name (unique)")
    tipo: LaudoTipoEnum = Field(..., description="Template type")
    conteudo: str = Field(..., description="Template content with placeholders")
    descricao: Optional[str] = Field(None, max_length=500)


class LaudoListResponse(BaseModel):
    """LA-06: Laudo list item (summary)."""

    id: int
    numero: str
    processo_id: int
    tipo: LaudoTipoEnum
    status: LaudoStatusEnum
    data_criacao: datetime
    data_assinatura: Optional[datetime] = None
    arquivo_docx_path: Optional[str] = None
    arquivo_pdf_path: Optional[str] = None

    class Config:
        from_attributes = True
