"""Pydantic schemas for Intimacao module."""

from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class IntimacaoCreateSchema(BaseModel):
    """Schema for creating a new Intimacao."""

    processo_id: int = Field(..., description="Process ID")
    origem: str = Field(..., max_length=50, description="Source: email, esaj, manual")
    tipo: Optional[str] = Field(None, max_length=50, description="Type: intimacao, notificacao, citacao")
    assunto: Optional[str] = Field(None, max_length=200)
    conteudo: Optional[str] = None
    pdf_path: Optional[str] = Field(None, max_length=500)
    txt_path: Optional[str] = Field(None, max_length=500)
    json_path: Optional[str] = Field(None, max_length=500)
    md_path: Optional[str] = Field(None, max_length=500)
    dados_estruturados: Optional[dict] = None
    status: Optional[str] = Field(default="pendente", max_length=50)
    erros: Optional[str] = None
    external_id: Optional[str] = Field(None, max_length=100)
    source_system: Optional[str] = Field(default="manual", max_length=50)

    class Config:
        from_attributes = True


class IntimacaoUpdateSchema(BaseModel):
    """Schema for updating an Intimacao."""

    tipo: Optional[str] = Field(None, max_length=50)
    assunto: Optional[str] = Field(None, max_length=200)
    conteudo: Optional[str] = None
    pdf_path: Optional[str] = Field(None, max_length=500)
    txt_path: Optional[str] = Field(None, max_length=500)
    json_path: Optional[str] = Field(None, max_length=500)
    md_path: Optional[str] = Field(None, max_length=500)
    dados_estruturados: Optional[dict] = None
    status: Optional[str] = Field(None, max_length=50)
    erros: Optional[str] = None

    class Config:
        from_attributes = True


class IntimacaoResponseSchema(BaseModel):
    """Schema for returning Intimacao data in responses."""

    id: int
    processo_id: int
    origem: str
    tipo: Optional[str]
    assunto: Optional[str]
    conteudo: Optional[str]
    pdf_path: Optional[str]
    txt_path: Optional[str]
    json_path: Optional[str]
    md_path: Optional[str]
    dados_estruturados: Optional[dict]
    status: Optional[str]
    erros: Optional[str]
    external_id: Optional[str]
    source_system: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class IntimacaoListSchema(BaseModel):
    """Simplified schema for Intimacao list responses."""

    id: int
    processo_id: int
    origem: str
    tipo: Optional[str]
    assunto: Optional[str]
    status: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
