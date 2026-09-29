"""Schemas for forensic analysis and laudo endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ClienteForenseResponse(BaseModel):
    """Cliente forense response schema."""
    nome: str
    cnpj: str
    email: str


class AnalisisResultResponse(BaseModel):
    """Analysis result response schema."""
    arquivo_hash: str
    veredicto_final: str
    confianca_consenso: float
    nivel_risco: str


class LaudoForenseResponse(BaseModel):
    """Laudo forense response schema."""
    numero_laudo: str
    cliente: ClienteForenseResponse
    arquivo_hash: str
    arquivo_nome: str
    arquivo_tamanho_mb: float
    veredicto: Optional[str] = "PROCESSANDO"
    authenticity_score: Optional[float] = None
    consensus: Optional[float] = None
    status: Optional[str] = "processando"
    pdf_url: Optional[str] = None
    created_at: Optional[str] = None
    resultados_apis: Optional[List[Dict[str, Any]]] = []


class LaudoForenseListItem(BaseModel):
    """Item in laudo forense list."""
    numero_laudo: str
    cliente: Optional[str] = None
    status: Optional[str] = "processando"
    veredicto: Optional[str] = None
    authenticity_score: Optional[float] = None
    created_at: Optional[str] = None


class LaudoForenseListResponse(BaseModel):
    """List of laudos forenses response."""
    total: int
    skip: int
    limit: int
    items: List[LaudoForenseListItem]


class CriarLaudoForenseRequest(BaseModel):
    """Request to create laudo forense."""
    cliente_nome: str = Field(..., min_length=3)
    cliente_cnpj: str
    cliente_email: str
    origem_midia: str = "Outro"
    descricao: Optional[str] = ""


class CriarLaudoForenseResponse(BaseModel):
    """Response when creating laudo forense."""
    numero_laudo: str
    status: str = "processando"
    job_id: str
    cliente: ClienteForenseResponse


class LaudoForenseCompleto(BaseModel):
    """Complete laudo forense schema."""
    numero_laudo: str
    cliente: ClienteForenseResponse
    arquivo_hash: str
    arquivo_nome: str
    arquivo_tamanho_mb: float
    veredicto: Optional[str] = None
    authenticity_score: Optional[float] = None
    consensus: Optional[float] = None
    status: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: Optional[datetime] = None
    resultados_apis: Optional[List[Dict[str, Any]]] = None
