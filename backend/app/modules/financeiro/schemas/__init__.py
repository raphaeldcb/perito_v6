"""
Financeiro module schemas — DTOs for Boleto, Nota, Honorario.

These schemas serve as interfaces for API communication and validation.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal


# ============================================================================
# BOLETO SCHEMAS
# ============================================================================

class BoletoBase(BaseModel):
    """Base schema for Boleto."""
    numero: str = Field(..., description="Número único do boleto")
    valor: Decimal = Field(..., gt=0, description="Valor do boleto")
    vencimento: date = Field(..., description="Data de vencimento")
    descricao: Optional[str] = Field(None, description="Descrição do boleto")


class BoletoCreate(BoletoBase):
    """Schema para criar novo boleto."""
    processo_id: int = Field(..., description="ID do processo relacionado")


class BoletoUpdate(BaseModel):
    """Schema para atualizar boleto."""
    status: Optional[str] = Field(None, description="Status do boleto")
    data_pagamento: Optional[datetime] = Field(None, description="Data de pagamento")
    desconto: Optional[Decimal] = Field(None, ge=0, description="Desconto aplicado")


class BoletoResponse(BoletoBase):
    """Response schema para Boleto."""
    id: int
    processo_id: int
    status: str
    inter_id: Optional[str] = None
    inter_url: Optional[str] = None
    qr_code: Optional[str] = None
    data_criacao: datetime
    data_emissao: Optional[datetime] = None
    data_pagamento: Optional[datetime] = None
    juros_multa: Decimal = Decimal("0.00")
    desconto: Decimal = Decimal("0.00")
    ativo: bool = True

    class Config:
        from_attributes = True


# ============================================================================
# NOTA SCHEMAS
# ============================================================================

class NotaBase(BaseModel):
    """Base schema for Nota."""
    numero: str = Field(..., description="Número da nota")
    valor: Decimal = Field(..., gt=0, description="Valor da nota")
    descricao: str = Field(..., description="Descrição da nota")
    data_emissao: date = Field(..., description="Data de emissão")


class NotaCreate(NotaBase):
    """Schema para criar nova nota."""
    processo_id: int = Field(..., description="ID do processo relacionado")
    nf_serie: Optional[str] = Field(None, description="Série da NF-e")
    nf_numero: Optional[str] = Field(None, description="Número da NF-e")
    nf_cnpj: Optional[str] = Field(None, description="CNPJ do emitente")


class NotaUpdate(BaseModel):
    """Schema para atualizar nota."""
    status: Optional[str] = Field(None, description="Status da nota")
    chave_acesso: Optional[str] = Field(None, description="Chave de acesso")


class NotaResponse(NotaBase):
    """Response schema para Nota."""
    id: int
    processo_id: int
    status: str
    nf_serie: Optional[str] = None
    nf_numero: Optional[str] = None
    nf_cnpj: Optional[str] = None
    url_acesso: Optional[str] = None
    chave_acesso: Optional[str] = None
    ativo: bool = True

    class Config:
        from_attributes = True


# ============================================================================
# HONORARIO SCHEMAS
# ============================================================================

class HonorarioBase(BaseModel):
    """Base schema for Honorario."""
    valor_base: Decimal = Field(..., gt=0, description="Valor base do processo")
    percentual: Decimal = Field(..., gt=0, description="Percentual de honorário")


class HonorarioCreate(HonorarioBase):
    """Schema para criar novo honorário."""
    processo_id: int = Field(..., description="ID do processo relacionado")
    observacoes: Optional[str] = Field(None, description="Observações")


class HonorarioUpdate(BaseModel):
    """Schema para atualizar honorário."""
    status_pagamento: Optional[str] = Field(None, description="Status de pagamento")
    data_pagamento: Optional[datetime] = Field(None, description="Data de pagamento")
    desconto: Optional[Decimal] = Field(None, ge=0, description="Desconto")
    acrescimo: Optional[Decimal] = Field(None, ge=0, description="Acréscimo")


class HonorarioResponse(HonorarioBase):
    """Response schema para Honorario."""
    id: int
    processo_id: int
    valor_final: Decimal
    status_pagamento: str
    desconto: Decimal = Decimal("0.00")
    acrescimo: Decimal = Decimal("0.00")
    data_pagamento: Optional[datetime] = None
    observacoes: Optional[str] = None
    ativo: bool = True

    class Config:
        from_attributes = True


__all__ = [
    "BoletoBase", "BoletoCreate", "BoletoUpdate", "BoletoResponse",
    "NotaBase", "NotaCreate", "NotaUpdate", "NotaResponse",
    "HonorarioBase", "HonorarioCreate", "HonorarioUpdate", "HonorarioResponse",
]
