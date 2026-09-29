from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ParticipanteDNACreate(BaseModel):
    tipo: str  # CRI, MA1, MA2, SP1-3, SMI1-3, ST1-3, AGM, AGF, OUTRO
    nome: str = Field(..., min_length=1, max_length=255)
    requerente: bool = False
    requerido: bool = False

class ParticipanteDNAUpdate(BaseModel):
    tipo: Optional[str] = None
    nome: Optional[str] = None
    requerente: Optional[bool] = None
    requerido: Optional[bool] = None

class ParticipanteDNAResponse(BaseModel):
    id: int
    processo_id: int
    tipo: str
    nome: str
    requerente: bool
    requerido: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EnquadramentoDNACreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20)
    descricao: str
    valor_particular: Optional[float] = None
    valor_judicial: Optional[float] = None
    resultado: str  # EXCLUSÃO ou INCLUSÃO
    probabilidade: Optional[float] = None  # % se INCLUSÃO
    observacoes: Optional[str] = None

class EnquadramentoDNAUpdate(BaseModel):
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    valor_particular: Optional[float] = None
    valor_judicial: Optional[float] = None
    resultado: Optional[str] = None
    probabilidade: Optional[float] = None
    observacoes: Optional[str] = None

class EnquadramentoDNAResponse(BaseModel):
    id: int
    processo_id: int
    codigo: str
    descricao: str
    valor_particular: Optional[float]
    valor_judicial: Optional[float]
    resultado: str
    probabilidade: Optional[float]
    observacoes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
