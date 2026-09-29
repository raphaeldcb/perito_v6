"""Engenharia schemas — request/response DTOs for vistoria operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Modelo Vistoria
# ============================================================================

class ModeloVistoriaResponse(BaseModel):
    """Response para listar modelos com resumo."""
    id: int
    area: str
    nome: str
    descricao: Optional[str] = None
    versao: int = 1
    icone: str = "📋"
    cor: str = "#2563eb"
    ativo: bool = True
    secoes: int = Field(description="Número de seções no schema")

    class Config:
        from_attributes = True


class ModeloVistoriaDetailResponse(BaseModel):
    """Response completa do modelo com schema."""
    id: int
    area: str
    nome: str
    descricao: Optional[str] = None
    versao: int = 1
    icone: str = "📋"
    cor: str = "#2563eb"
    ativo: bool = True
    schema: Dict[str, Any] = Field(default_factory=lambda: {"secoes": []})

    class Config:
        from_attributes = True


class ModeloVistoriaCreateRequest(BaseModel):
    """Request para criar modelo."""
    nome: str
    area: str = "engenharia"
    descricao: Optional[str] = None
    schema: Dict[str, Any] = Field(default_factory=lambda: {"secoes": []})
    icone: str = "📋"
    cor: str = "#2563eb"
    ativo: bool = True


class ModeloVistoriaUpdateRequest(BaseModel):
    """Request para atualizar modelo."""
    nome: Optional[str] = None
    area: Optional[str] = None
    descricao: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    icone: Optional[str] = None
    cor: Optional[str] = None
    ativo: Optional[bool] = None


class ModeloVistoriaCreateResponse(BaseModel):
    """Response após criar modelo."""
    id: int
    nome: str
    versao: int = 1


# ============================================================================
# Vistorias
# ============================================================================

class VistoriaFotoResponse(BaseModel):
    """Response de foto de vistoria."""
    id: int
    campo_key: Optional[str] = None
    obrigatoria: bool = False
    legenda: Optional[str] = None
    arquivo_path: str

    class Config:
        from_attributes = True


class VistoriaAssinaturaResponse(BaseModel):
    """Response de assinatura de vistoria."""
    id: int
    nome: str
    documento: str
    papel: str

    class Config:
        from_attributes = True


class VistoriaResponse(BaseModel):
    """Response para vistoria resumida."""
    id: int
    modelo_id: int
    modelo_versao: int
    modelo_nome: Optional[str] = None
    processo_id: Optional[int] = None
    local: Optional[str] = None
    gps: Optional[str] = None
    status: str
    dados: Dict[str, Any] = Field(default_factory=dict)
    uuid_offline: Optional[str] = None
    pdf_path: Optional[str] = None
    fotos: int = Field(description="Número de fotos")
    assinaturas: int = Field(description="Número de assinaturas")
    criado_em: Optional[str] = None

    class Config:
        from_attributes = True


class VistoriaDetailResponse(BaseModel):
    """Response completa da vistoria com fotos e assinaturas."""
    id: int
    modelo_id: int
    modelo_versao: int
    modelo_nome: Optional[str] = None
    processo_id: Optional[int] = None
    local: Optional[str] = None
    gps: Optional[str] = None
    status: str
    dados: Dict[str, Any] = Field(default_factory=dict)
    uuid_offline: Optional[str] = None
    pdf_path: Optional[str] = None
    fotos_lista: List[VistoriaFotoResponse] = Field(default_factory=list)
    assinaturas_lista: List[VistoriaAssinaturaResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class VistoriaCreateRequest(BaseModel):
    """Request para criar/upsert vistoria."""
    modelo_id: int
    processo_id: Optional[int] = None
    local: Optional[str] = None
    gps: Optional[str] = None
    dados: Dict[str, Any] = Field(default_factory=dict)
    uuid_offline: Optional[str] = None
    criado_offline_em: Optional[str] = None
    status: Optional[str] = None


class VistoriaEnviarRequest(BaseModel):
    """Request para finalizar e enviar vistoria."""
    processo_id: Optional[int] = None


class VistoriaAssinaturaPdfRequest(BaseModel):
    """Request para registrar assinatura digital no PDF."""
    hash_assinatura: str
    certificado_cn: str
    data_assinatura: Optional[str] = None
    timestamp_server_url: Optional[str] = None


class VistoriaFotoCreateRequest(BaseModel):
    """Request para adicionar foto à vistoria."""
    base64_data: str = Field(description="Dados da foto em base64")
    campo_key: Optional[str] = None
    legenda: Optional[str] = None
    ordem: Optional[int] = None


class VistoriaEnviarResponse(BaseModel):
    """Response após enviar vistoria."""
    id: int
    status: str
    processo_id: Optional[int] = None
    pdf_gerado: bool


class VistoriaFotoResponse(BaseModel):
    """Response após adicionar foto."""
    id: int
    vistoria_id: int
    arquivo_path: str
    legenda: Optional[str] = None


class VistoriaAssinaturaResponse(BaseModel):
    """Response após registrar assinatura."""
    id: int
    status: str
    assinado_em: Optional[str] = None
    certificado: Optional[str] = None


class LaudoVistoriaResponse(BaseModel):
    """Response do laudo gerado."""
    id: int
    laudo_rascunho: str
    resumo: Optional[str] = None
