"""
Pydantic schemas for ProjetoCP Phase 2 Laudos (input/output validation)
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AreaPericia(str, Enum):
    GRAFOTECNICA = "grafotecnica"
    ENGENHARIA_CIVIL = "engenharia_civil"
    ENGENHARIA_MECANICA = "engenharia_mecanica"
    ENGENHARIA_ELETRICA = "engenharia_eletrica"
    AGRONOMIA = "agronomia"
    MEDICINA = "medicina"
    ODONTOLOGIA = "odontologia"
    PSICOLOGIA = "psicologia"
    CONTABILIDADE = "contabilidade"
    ECONOMIA = "economia"
    TOPOGRAFIA = "topografia"
    DESLOCAMENTO = "deslocamento"


class LaudoStatus(str, Enum):
    RASCUNHO = "rascunho"
    ESTRUTURADO = "estruturado"
    CONTEUDO_INICIAL = "conteudo_inicial"
    RESPALDO_COMPLETO = "respaldo_completo"
    REVISAO_INTERNA = "revisao_interna"
    REVISAO_CLIENTE = "revisao_cliente"
    PRONTO_PROTOCOLO = "pronto_protocolo"
    PROTOCOLADO = "protocolado"
    FINALIZADO = "finalizado"


# ============ LaudoQuesito Schemas ============

class LaudoQuesitoCriarRequest(BaseModel):
    laudo_id: int
    numero: int
    pergunta: str
    tipo: str = "ordinario"
    relevancia: int = Field(default=5, ge=1, le=10)

    class Config:
        from_attributes = True


class LaudoQuesitoAtualizar(BaseModel):
    resposta: Optional[str] = None
    tipo: Optional[str] = None
    relevancia: Optional[int] = None
    status: Optional[str] = None
    fontes_rag: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class LaudoQuesitoResponse(BaseModel):
    id: int
    laudo_id: int
    numero: int
    pergunta: str
    resposta: Optional[str]
    tipo: str
    relevancia: int
    fontes_rag: Optional[List[Dict[str, Any]]]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ LaudoAnexo Schemas ============

class LaudoAnexoCriarRequest(BaseModel):
    laudo_id: int
    tipo: str
    titulo: str
    descricao: Optional[str] = None
    arquivo_path: str
    pagina_referencia: Optional[int] = None
    mime_type: Optional[str] = None

    class Config:
        from_attributes = True


class LaudoAnexoResponse(BaseModel):
    id: int
    laudo_id: int
    tipo: str
    titulo: str
    descricao: Optional[str]
    arquivo_path: str
    pagina_referencia: Optional[int]
    tamanho_bytes: Optional[int]
    mime_type: Optional[str]
    upload_por_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ LaudoHonorario Schemas ============

class LaudoHonorarioCriarRequest(BaseModel):
    laudo_id: int
    processo_id: int
    area: AreaPericia
    tipo_calculo: str = "tabela"
    valor_base: Decimal
    adicional_complexidade: Decimal = Decimal(0)
    adicional_deslocamento: Decimal = Decimal(0)
    deducao_desconto: Decimal = Decimal(0)
    percentual_sucumbencia: Optional[Decimal] = None

    @validator("valor_base", "adicional_complexidade", "adicional_deslocamento", "deducao_desconto")
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError("Valores não podem ser negativos")
        return v

    class Config:
        from_attributes = True


class LaudoHonorarioResponse(BaseModel):
    id: int
    laudo_id: int
    processo_id: int
    area: str
    tipo_calculo: str
    valor_base: Decimal
    adicional_complexidade: Decimal
    adicional_deslocamento: Decimal
    deducao_desconto: Decimal
    valor_final: Decimal
    percentual_sucumbencia: Optional[Decimal]
    data_calculo: datetime
    calculado_por_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ LaudoRevenda Schemas ============

class LaudoRevendaResponse(BaseModel):
    id: int
    laudo_id: int
    versao_numero: int
    etapa: str
    modelo_ia: str
    tempo_processamento_segundos: Optional[int]
    status: str
    erro: Optional[str]
    processado_por: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Extended Laudo Response (Composite) ============

class LaudoCompletoResponse(BaseModel):
    id: int
    processo_id: int
    tipo_laudo: str
    status: LaudoStatus
    perito_id: int
    revisor_id: Optional[int]
    empresa_id: int
    data_criacao: datetime
    data_emissao: Optional[datetime]
    data_assinatura: Optional[datetime]
    assinado_por: Optional[str]
    arquivo_docx_path: Optional[str]
    arquivo_pdf_path: Optional[str]
    quesitos: List[LaudoQuesitoResponse] = []
    anexos: List[LaudoAnexoResponse] = []
    honorario: Optional[LaudoHonorarioResponse] = None
    revenda_log: List[LaudoRevendaResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Auto-Generation Request ============

class LaudoGeracaoAutomaticaRequest(BaseModel):
    laudo_id: int
    processo_id: int
    area: AreaPericia
    etapa: str = "extracao_quesitos"  # extracao_quesitos, geracao_conteudo, revisao
    usar_rag: bool = True
    modelo_ia: str = "qwen-3.6"

    class Config:
        from_attributes = True


class LaudoGeracaoResponse(BaseModel):
    job_id: int
    laudo_id: int
    status: str
    etapa: str
    mensagem: str
    estimado_em_segundos: int = 60

    class Config:
        from_attributes = True
