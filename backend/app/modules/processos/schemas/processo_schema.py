"""Pydantic schemas for Processo module."""

from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ProcessoCreateSchema(BaseModel):
    """Schema for creating a new Processo."""

    numero_cnj: str = Field(..., min_length=1, max_length=25, description="CNJ process number")
    titulo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = None
    autor: Optional[str] = Field(None, max_length=200)
    reu: Optional[str] = Field(None, max_length=200)
    especialidade: Optional[str] = Field(None, max_length=100)
    vara: Optional[str] = Field(None, max_length=100)
    tribunal: Optional[str] = Field(None, max_length=100)
    juiz: Optional[str] = Field(None, max_length=200)
    comarca: Optional[str] = Field(None, max_length=100)
    tipo_pericia: Optional[str] = Field(default="Judicial", max_length=50)
    setor: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(default="protocolado", max_length=50)
    prioridade: Optional[str] = Field(default="Média", max_length=20)
    honorarios: Optional[Decimal] = None
    forma_recebimento: Optional[str] = Field(None, max_length=20)
    pago: Optional[bool] = False
    prazo: Optional[datetime] = None
    responsavel_id: Optional[int] = None
    partes: Optional[List[Any]] = Field(default_factory=list)
    laboratorio: Optional[str] = Field(None, max_length=150)
    deslocamento: Optional[dict] = None
    documentos: Optional[List[Any]] = Field(default_factory=list)
    decisao_oficial_path: Optional[str] = Field(None, max_length=500)

    class Config:
        from_attributes = True


class ProcessoUpdateSchema(BaseModel):
    """Schema for updating an existing Processo."""

    titulo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = None
    autor: Optional[str] = Field(None, max_length=200)
    reu: Optional[str] = Field(None, max_length=200)
    especialidade: Optional[str] = Field(None, max_length=100)
    vara: Optional[str] = Field(None, max_length=100)
    tribunal: Optional[str] = Field(None, max_length=100)
    juiz: Optional[str] = Field(None, max_length=200)
    comarca: Optional[str] = Field(None, max_length=100)
    tipo_pericia: Optional[str] = Field(None, max_length=50)
    setor: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    prioridade: Optional[str] = Field(None, max_length=20)
    honorarios: Optional[Decimal] = None
    forma_recebimento: Optional[str] = Field(None, max_length=20)
    pago: Optional[bool] = None
    prazo: Optional[datetime] = None
    partes: Optional[List[Any]] = None
    laboratorio: Optional[str] = Field(None, max_length=150)
    deslocamento: Optional[dict] = None
    documentos: Optional[List[Any]] = None
    decisao_oficial_path: Optional[str] = Field(None, max_length=500)

    class Config:
        from_attributes = True


class ProcessoResponseSchema(BaseModel):
    """Schema for returning Processo data in responses."""

    id: int
    numero_cnj: str
    titulo: Optional[str]
    descricao: Optional[str]
    autor: Optional[str]
    reu: Optional[str]
    especialidade: Optional[str]
    vara: Optional[str]
    tribunal: Optional[str]
    juiz: Optional[str]
    comarca: Optional[str]
    tipo_pericia: Optional[str]
    setor: Optional[str]
    status: Optional[str]
    prioridade: Optional[str]
    honorarios: Optional[Decimal]
    forma_recebimento: Optional[str]
    pago: Optional[bool]
    prazo: Optional[datetime]
    responsavel_id: Optional[int]
    partes: Optional[List[Any]]
    laboratorio: Optional[str]
    deslocamento: Optional[dict]
    documentos: Optional[List[Any]]
    decisao_oficial_path: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProcessoListSchema(BaseModel):
    """Simplified schema for list responses."""

    id: int
    numero_cnj: str
    titulo: Optional[str]
    autor: Optional[str]
    reu: Optional[str]
    vara: Optional[str]
    comarca: Optional[str]
    setor: Optional[str]
    status: Optional[str]
    prioridade: Optional[str]
    honorarios: Optional[Decimal]
    responsavel_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
