"""
ProjetoCP Schemas — Pydantic models para validação input/output.

PHASE 1: Request/Response models
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============== Enums (repetidos aqui por simplicidade) ==============

class StatusComarca(str, Enum):
    ATIVO = "Ativo"
    INATIVO = "Inativo"


class StatusVara(str, Enum):
    ATIVO = "Ativo"
    INATIVO = "Inativo"


class StatusJuiz(str, Enum):
    ATIVO = "Ativo"
    APOSENTADO = "Aposentado"
    SUBSTITUIDO = "Substituído"


class StatusProcesso(str, Enum):
    PROTOCOLADO = "Protocolado"
    EM_ANDAMENTO = "Em Andamento"
    CONCLUIDO = "Concluído"
    CANCELADO = "Cancelado"
    ARQUIVADO = "Arquivado"


class TipoPericia(str, Enum):
    JUDICIAL = "Judicial"
    EXTRAJUDICIAL = "Extrajudicial"
    AT = "AT"


# ============== Comarca Schemas ==============

class ComarcaCreate(BaseModel):
    """Schema para criar Comarca."""
    nome: str = Field(..., min_length=1, max_length=255)
    codigo_cnj: Optional[str] = Field(None, max_length=20)
    uf: str = Field(..., min_length=2, max_length=2)
    municipio: Optional[str] = Field(None, max_length=150)
    status: StatusComarca = StatusComarca.ATIVO


class ComarcaUpdate(BaseModel):
    """Schema para atualizar Comarca."""
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    codigo_cnj: Optional[str] = Field(None, max_length=20)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    municipio: Optional[str] = Field(None, max_length=150)
    status: Optional[StatusComarca] = None


class ComarcaRead(BaseModel):
    """Schema para ler Comarca."""
    id: int
    nome: str
    codigo_cnj: Optional[str]
    uf: str
    municipio: Optional[str]
    status: StatusComarca
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== Vara Schemas ==============

class VaraCreate(BaseModel):
    """Schema para criar Vara."""
    comarca_id: int
    nome: str = Field(..., min_length=1, max_length=255)
    codigo_cnj: Optional[str] = Field(None, max_length=20)
    tipo: Optional[str] = Field(None, max_length=100)  # Cível, Criminal, etc.
    status: StatusVara = StatusVara.ATIVO
    observacoes: Optional[str] = None


class VaraUpdate(BaseModel):
    """Schema para atualizar Vara."""
    comarca_id: Optional[int] = None
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    codigo_cnj: Optional[str] = Field(None, max_length=20)
    tipo: Optional[str] = Field(None, max_length=100)
    status: Optional[StatusVara] = None
    observacoes: Optional[str] = None


class VaraRead(BaseModel):
    """Schema para ler Vara."""
    id: int
    comarca_id: int
    nome: str
    codigo_cnj: Optional[str]
    tipo: Optional[str]
    status: StatusVara
    observacoes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== Juiz Schemas ==============

class JuizCreate(BaseModel):
    """Schema para criar Juiz."""
    comarca_id: int
    vara_id: Optional[int] = None
    nome: str = Field(..., min_length=1, max_length=255)
    cpf: Optional[str] = Field(None, max_length=20)
    registro_cnj: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    telefone: Optional[str] = Field(None, max_length=20)
    status: StatusJuiz = StatusJuiz.ATIVO
    observacoes: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and "@" not in v:
            raise ValueError("Email inválido")
        return v


class JuizUpdate(BaseModel):
    """Schema para atualizar Juiz."""
    comarca_id: Optional[int] = None
    vara_id: Optional[int] = None
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    cpf: Optional[str] = Field(None, max_length=20)
    registro_cnj: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    telefone: Optional[str] = Field(None, max_length=20)
    status: Optional[StatusJuiz] = None
    observacoes: Optional[str] = None


class JuizRead(BaseModel):
    """Schema para ler Juiz."""
    id: int
    comarca_id: int
    vara_id: Optional[int]
    nome: str
    cpf: Optional[str]
    registro_cnj: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    status: StatusJuiz
    observacoes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== Processo Schemas ==============

class ProcessoCreate(BaseModel):
    """Schema para criar Processo."""
    numero_cnj: str = Field(..., min_length=1, max_length=50)
    empresa_id: Optional[int] = None
    tipo: str = Field("Judicial", max_length=50)
    tipo_pericia: TipoPericia = TipoPericia.JUDICIAL
    setor: str = Field(..., max_length=50)  # 01-Contábil, 02-Engenharia
    status: StatusProcesso = StatusProcesso.PROTOCOLADO
    prioridade: Optional[str] = Field("Média", max_length=20)
    comarca_id: Optional[int] = None
    vara_id: Optional[int] = None
    juiz_id: Optional[int] = None
    partes: Optional[List[dict]] = Field(default_factory=list)
    participantes_dna: Optional[List[dict]] = Field(default_factory=list)
    laboratorio: Optional[str] = Field(None, max_length=150)
    deslocamento: Optional[dict] = None
    valor_causa: Optional[str] = Field(None, max_length=50)
    documentos: Optional[List[dict]] = Field(default_factory=list)
    responsavel_id: Optional[int] = None
    observacoes: Optional[str] = None


class ProcessoUpdate(BaseModel):
    """Schema para atualizar Processo (partial)."""
    tipo: Optional[str] = Field(None, max_length=50)
    tipo_pericia: Optional[TipoPericia] = None
    setor: Optional[str] = Field(None, max_length=50)
    status: Optional[StatusProcesso] = None
    prioridade: Optional[str] = Field(None, max_length=20)
    comarca_id: Optional[int] = None
    vara_id: Optional[int] = None
    juiz_id: Optional[int] = None
    partes: Optional[List[dict]] = None
    participantes_dna: Optional[List[dict]] = None
    laboratorio: Optional[str] = Field(None, max_length=150)
    deslocamento: Optional[dict] = None
    valor_causa: Optional[str] = Field(None, max_length=50)
    documentos: Optional[List[dict]] = None
    responsavel_id: Optional[int] = None
    observacoes: Optional[str] = None


class ProcessoRead(BaseModel):
    """Schema para ler Processo."""
    id: int
    numero_cnj: str
    empresa_id: Optional[int]
    tipo: Optional[str] = None
    tipo_pericia: Optional[TipoPericia] = None
    setor: Optional[str] = None
    status: Optional[StatusProcesso] = None
    prioridade: Optional[str] = None
    comarca_id: Optional[int] = None
    vara_id: Optional[int] = None
    juiz_id: Optional[int] = None
    partes: Optional[List[dict]] = None
    participantes_dna: Optional[List[dict]] = None
    laboratorio: Optional[str] = None
    deslocamento: Optional[dict] = None
    valor_causa: Optional[str] = None
    documentos: Optional[List[dict]] = None
    responsavel_id: Optional[int] = None
    observacoes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProcessoListResponse(BaseModel):
    """Schema para listar Processos (com paginação)."""
    total: int
    skip: int
    limit: int
    items: List[ProcessoRead]
