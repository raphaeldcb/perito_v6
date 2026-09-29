from pydantic import BaseModel
from typing import List, Optional


class ModeloResponse(BaseModel):
    id: int
    nome: str
    descricao: str
    categoria: str
    ativo: bool


class IntimacaoUploadResponse(BaseModel):
    id: int
    processo_id: int
    numero_processo: str
    status: str
    message: str


class BaixarAutosESAJRequest(BaseModel):
    numero_processo: str
    tribunal: str = "TJMS"
    sistema: str = "esaj"  # esaj | eproc


class BaixarAutosESAJResponse(BaseModel):
    job_id: int
    numero_processo: str
    status: str
    message: str


class IntimacaoArquivoResponse(BaseModel):
    conteudo: Optional[str] = None
    tipo: str


class IntimacaoResumoItem(BaseModel):
    id: int
    numero_cnj: str
    data_processamento: Optional[str]
    status: str
    juiz: str
    vara: str
    tipo: str
    prazo_dias: int
    urgencia: str
    resumo: str
    quesitos_count: int
    arquivos: dict


class IntimacaoResumoResponse(BaseModel):
    total: int
    itens: List[IntimacaoResumoItem]


class IntimacaoStatusUpdateRequest(BaseModel):
    novo_status: str
