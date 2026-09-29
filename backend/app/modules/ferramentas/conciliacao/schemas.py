"""Pydantic schemas para conciliação."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CorrigirRequest(BaseModel):
    """Request para cálculo de fator de correção."""
    valor: float = Field(..., description="Valor a ser corrigido")
    de: str = Field(..., description="Data inicial (YYYY-MM-DD ou DD/MM/YYYY)")
    ate: str = Field(..., description="Data final (YYYY-MM-DD ou DD/MM/YYYY)")
    indexador: str = Field(default="IPCA", description="Índice a usar (IPCA, IPCA-E, INPC, IGPM)")


class CorrigirResponse(BaseModel):
    """Response do cálculo de correção."""
    valor: float
    de: str
    ate: str
    indexador: str
    fator: float
    corrigido: float


class CandidatoProposta(BaseModel):
    """Candidato para conciliação."""
    processo_id: Optional[int] = None
    numero_cnj: Optional[str] = None
    honorario: float
    data_proposta: str = Field(..., description="Data da proposta (YYYY-MM-DD ou DD/MM/YYYY)")


class ConciliarRequest(BaseModel):
    """Request para conciliação de crédito."""
    valor: float = Field(..., description="Valor do crédito")
    data_credito: str = Field(..., description="Data do crédito (YYYY-MM-DD ou DD/MM/YYYY)")
    tolerancia: float = Field(default=0.12, description="Tolerância de diferença (0-1)")
    indexador: str = Field(default="IPCA", description="Índice a usar")
    candidatos: Optional[List[CandidatoProposta]] = Field(default=None, description="Lista de candidatos; se None, usa processos com honorário")


class ConciliarMatch(BaseModel):
    """Item de match na conciliação."""
    processo_id: Optional[int] = None
    numero_cnj: Optional[str] = None
    honorario: float
    valor_esperado: float
    diferenca_pct: float
    score: float
    casa: bool
    alerta: Optional[str] = None


class ConciliarResponse(BaseModel):
    """Response da conciliação."""
    total_candidatos: int
    matches: List[ConciliarMatch] = Field(description="Top matches (casa=true)")
    top: List[Dict[str, Any]] = Field(description="Top 5 por score")
