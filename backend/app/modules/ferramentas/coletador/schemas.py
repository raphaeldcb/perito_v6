"""Schemas for coletador CNAB payment module."""
from typing import List, Optional
from pydantic import BaseModel, Field


class BeneficiarioPagamento(BaseModel):
    """Beneficiário para pagamento CNAB."""
    nome: str = Field(..., min_length=1, max_length=30)
    cpf: str = Field(..., pattern=r"^\d{11}$")
    agencia: str = Field(..., pattern=r"^\d{1,5}$")
    conta: str = Field(..., pattern=r"^\d{1,12}$")
    dv: str = Field(..., pattern=r"^\d$")
    valor: int = Field(..., gt=0)  # Em centavos


class GerarCNABRequest(BaseModel):
    """Request para gerar arquivo CNAB."""
    beneficiarios: List[BeneficiarioPagamento] = Field(..., min_items=1)
    data_pagamento: Optional[str] = Field(None, pattern=r"^\d{8}$|^$")  # DDMMYYYY ou vazio
    descricao: Optional[str] = Field(None, max_length=100)


class ValidarCNABResponse(BaseModel):
    """Response para validação CNAB."""
    status: str
    beneficiarios: int
    valor_total: float
    mensagens: List[str]


class GerarCNABResponse(BaseModel):
    """Response para geração CNAB."""
    status: str
    arquivo: str
    beneficiarios: int
    valor_total: float
    linhas: int
    data_pagamento: str
    conteudo_preview: List[str]
