"""Cerebro (IA Coordination) — Schemas for workflows, triggers, and intelligence."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Workflow Schemas (from cerebro_advanced.py)
# ============================================================================

class WorkflowDeployRequest(BaseModel):
    """Deploy de workflow template."""
    tipo: str = Field(..., description="processo_criado, intimacao_recebida, etc.")
    nome_customizado: Optional[str] = None
    sla_minutos: Optional[int] = None
    ativa: bool = True

    class Config:
        example = {
            "tipo": "processo_criado",
            "nome_customizado": "Meu Workflow Personalizado",
            "sla_minutos": 120,
            "ativa": True
        }


class WorkflowExecutionResponse(BaseModel):
    """Resultado de execução de workflow."""
    id: int
    definition_id: int
    status: str  # running, completed, failed
    trigger_event: str
    trigger_id: Optional[int]
    node_results: Dict[str, Any]
    iniciado_em: datetime
    concluido_em: Optional[datetime]


class TriggerCustomizado(BaseModel):
    """Trigger customizado (condition builder)."""
    nome: str
    descricao: Optional[str]
    condicao: str  # "campo == valor AND campo2 >= valor2"
    acao: str  # "disparar_workflow", "enviar_email", "escalar"
    acao_config: Dict[str, Any]
    ativa: bool = True

    class Config:
        example = {
            "nome": "Processo >R$1M dispara risco",
            "condicao": "valor > 1000000",
            "acao": "disparar_workflow",
            "acao_config": {"workflow_id": 5}
        }


class BatchJobRequest(BaseModel):
    """Requisição para batch workflow (100+ processos)."""
    workflow_id: int
    filtro_processos: Dict[str, Any]  # ex: {"area": "grafotecnica", "status": "novo"}
    paralelizar: int = 5  # Max workers paralelos

    class Config:
        example = {
            "workflow_id": 1,
            "filtro_processos": {
                "area": "grafotecnica",
                "status": "novo",
                "valor_max": 500000
            },
            "paralelizar": 10
        }


class SLAStatus(BaseModel):
    """Status de SLA de um workflow."""
    workflow_id: int
    nome: str
    sla_minutos: int
    em_execucao: int
    percentual_prazo: float  # Percentual
    alertas: int  # Total com alerta
    tempo_medio_min: float


# ============================================================================
# Learning & Intelligence Schemas (from cerebro.py)
# ============================================================================

class AprendizadoEventoRequest(BaseModel):
    """Registra novo aprendizado (evento)."""
    tipo: str = Field(..., description="job_concluido, intimacao_recebida, laudo_gerado, etc.")
    contexto: Dict[str, Any] = Field(default_factory=dict)
    origem: str = Field(default="manual", description="esaj, meta, job_queue, financeiro, etc.")
    padrão_id: Optional[int] = None
    idempotency_key: Optional[str] = None


class RecomendacaoResponse(BaseModel):
    """Recomendação inteligente por contexto."""
    context: str
    recommendation: str
    confidence: float
    exemplos: List[int] = []
    padrões_alternativos: List[str] = []


class ConhecimentoBaseResponse(BaseModel):
    """Base de conhecimento RAG por departamento."""
    domain: str
    query: Optional[str] = None
    resultados: int
    knowledge_base: List[Dict[str, Any]] = []
