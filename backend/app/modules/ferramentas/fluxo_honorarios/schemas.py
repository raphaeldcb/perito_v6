"""Schemas for fluxo_honorarios (honorarium flow) module."""
from typing import Optional, List
from pydantic import BaseModel, Field


class JuizoImportItem(BaseModel):
    """Item de histórico de juízo para importação."""
    comarca: Optional[str] = None
    vara: Optional[str] = None
    proposta: int = 0
    ratifica: int = 0
    declina: int = 0


class JuizosImportBody(BaseModel):
    """Body para importar histórico de juízos."""
    juizos: List[JuizoImportItem] = Field(default_factory=list)


class OficioGerarBody(BaseModel):
    """Body para gerar ofício."""
    processo_id: int
    situacao: str = "proposta"
    valor_proposto: Optional[float] = None
    valor_arbitrado: Optional[float] = None
    valor_majorado: Optional[float] = None
    objeto: Optional[str] = None
    prestador: str = "47"
    intimacao_id: Optional[int] = None


class DecidirBody(BaseModel):
    """Body para decidir honorários."""
    processo_id: int
    situacao: str = "impugnacao"
    juiz_nome: Optional[str] = None
    valor_proposto: Optional[float] = None
    valor_arbitrado: Optional[float] = None


class RegistrarAtuacaoBody(BaseModel):
    """Body para registrar atuação de juízo."""
    juiz_nome: str
    comarca: Optional[str] = None
    vara: Optional[str] = None
    reduziu: bool = False
    reducao_pct: Optional[float] = None
    homologou: bool = False
    declinamos: bool = False


class MarcaNuncaPagaBody(BaseModel):
    """Body para marcar juízo como nunca_paga."""
    nunca_paga: bool = True
