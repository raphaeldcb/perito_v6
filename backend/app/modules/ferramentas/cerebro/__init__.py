"""Cerebro (IA Coordination) — Isolated module combining cerebro.py + cerebro_advanced.py.

This module provides:
- Core intelligence endpoints (graph, learn, recommend, knowledge)
- Workflow management (deploy, execute, trigger, batch)
- Monitoring (SLA, escalations)
- Escalation handling

Exports:
- cerebro_router: FastAPI router with all endpoints
- Schemas: Pydantic models for requests/responses
- Services: Business logic classes
"""

from .router import router as cerebro_router
from .router import router
from .schemas import (
    WorkflowDeployRequest,
    WorkflowExecutionResponse,
    TriggerCustomizado,
    BatchJobRequest,
    SLAStatus,
    AprendizadoEventoRequest,
    RecomendacaoResponse,
    ConhecimentoBaseResponse,
)
from .service import (
    WorkflowTemplates,
    WorkflowBuilder,
    classify_event_pattern,
    EscalationEngine,
    EscalationReason,
)

__all__ = [
    # Router (FastAPI integration)
    "cerebro_router",
    # Schemas
    "WorkflowDeployRequest",
    "WorkflowExecutionResponse",
    "TriggerCustomizado",
    "BatchJobRequest",
    "SLAStatus",
    "AprendizadoEventoRequest",
    "RecomendacaoResponse",
    "ConhecimentoBaseResponse",
    # Services
    "WorkflowTemplates",
    "WorkflowBuilder",
    "classify_event_pattern",
    "EscalationEngine",
    "EscalationReason",
]
