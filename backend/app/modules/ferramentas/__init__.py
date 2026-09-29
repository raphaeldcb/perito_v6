"""
Ferramentas module — Calculator utilities, CNJ parsing, RAG search, and more.

Wave 1 Modularization: Isolated submodules with self-contained router, schemas, service.
Internal implementation (models, repositories, centralized directories) removed.

Modularized, stateless utility services with no external dependencies.
Pure Python calculations: deslocamento (travel), juros (interest), CNJ parsing, RAG (pgvector).

All services are singletons (thread-safe) and stateless (deterministic).
p95 latency < 10ms for all operations.

Exports:
- Schemas: DeslocamentoRequest, JurosRequest, CNJRequest, Chunk, etc. (PUBLIC DTOs)
- Routers: calculator_router, cnj_router, rag_router, engenharia_router, etc. (FastAPI integration)

Never import services directly — they're internal implementation.
All inter-module communication via app.shared DTOs and exceptions.
"""

from .calculator import (
    DeslocamentoRequest,
    DeslocamentoResponse,
    JurosRequest,
    JurosResponse,
    CalculatorResponse,
    router as calculator_router,
)
from .cnj import (
    CNJRequest,
    CNJResponse,
    CNJParseResult,
    router as cnj_router,
)
from .diario import (
    ConfigInput,
    ConsultaInput,
    AnalisarInput,
    router as diario_router,
)
from .rag import (
    Chunk,
    IndexarInput,
    BuscarInput,
    router as rag_router,
)
from .dna import (
    router as dna_router,
)
from .dashboard_alertas import (
    DashboardAlerta,
    router as dashboard_alertas_router,
)
from .coletador import (
    BeneficiarioPagamento,
    GerarCNABRequest,
    ValidarCNABResponse,
    GerarCNABResponse,
    router as coletador_router,
)
from .forensic import (
    router as forensic_router,
)
from .deslocamento import (
    router as deslocamento_router,
)
from .engenharia import (
    router as engenharia_router,
)
from .cerebro import (
    cerebro_router,
)
from .auto_laudo_pro import (
    ProcessUploadRequest,
    ExtracaoResponse,
    LaudoGeradoResponse,
    ValidarEficienciaResponse,
    ExtractionData,
    QuesitosAgrupados,
    Quesito,
    router as auto_laudo_pro_router,
)

__all__ = [
    # Calculator Schemas
    "DeslocamentoRequest",
    "DeslocamentoResponse",
    "JurosRequest",
    "JurosResponse",
    "CalculatorResponse",
    # CNJ Schemas
    "CNJRequest",
    "CNJResponse",
    "CNJParseResult",
    # Diario Schemas
    "ConfigInput",
    "ConsultaInput",
    "AnalisarInput",
    # RAG Schemas
    "Chunk",
    "IndexarInput",
    "BuscarInput",
    # Dashboard Alertas Schemas
    "DashboardAlerta",
    # Coletador Schemas
    "BeneficiarioPagamento",
    "GerarCNABRequest",
    "ValidarCNABResponse",
    "GerarCNABResponse",
    # AutoLaudoPro Schemas
    "ProcessUploadRequest",
    "ExtracaoResponse",
    "LaudoGeradoResponse",
    "ValidarEficienciaResponse",
    "ExtractionData",
    "QuesitosAgrupados",
    "Quesito",
    # Routers (PUBLIC — FastAPI integration)
    "calculator_router",
    "cnj_router",
    "diario_router",
    "rag_router",
    "dna_router",
    "dashboard_alertas_router",
    "coletador_router",
    "deslocamento_router",
    "forensic_router",
    "engenharia_router",
    "cerebro_router",
    "auto_laudo_pro_router",
]
