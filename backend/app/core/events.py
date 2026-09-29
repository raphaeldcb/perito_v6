"""
Domain event types for all modules.

Each module emits domain events that decouple modules:
- Processos module: ProcessoCreated, ProcessoUpdated
- Laudos module: LaudoGenerated, LaudoPublished
- Financeiro module: BoletoSynced, ReceitaRecorded
- ESAJ module: IntimacaoReceived, IntimacaoBumped
- IA module: AnalysisCompleted

Events are immutable, serializable, and include payload + metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum

from app.core.event_bus import Event


class ProcessoStatus(str, Enum):
    """Status enum for processo lifecycle."""

    NOVO = "novo"
    EM_ANALISE = "em_analise"
    EM_LAUDO = "em_laudo"
    PRONTO = "pronto"
    ARQUIVADO = "arquivado"


@dataclass
class ProcessoCreated(Event):
    """Emitted when a new processo is created in processos module."""

    event_type: str = "ProcessoCreated"
    module: str = "processos"

    processo_id: int = 0
    numero: str = ""  # e.g., "0001234-56.2024.8.28.0100"
    valor: float = 0.0
    area_id: Optional[int] = None
    tipo_pericia: Optional[str] = None  # JUDICIAL, EXTRAJUDICIAL, AT

    def __post_init__(self):
        """Validate and set defaults."""
        super().__post_init__()


@dataclass
class ProcessoUpdated(Event):
    """Emitted when a processo is updated."""

    event_type: str = "ProcessoUpdated"
    module: str = "processos"

    processo_id: int = 0
    status: str = ProcessoStatus.EM_ANALISE
    updated_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LaudoGenerated(Event):
    """Emitted when a laudo is generated in laudos module."""

    event_type: str = "LaudoGenerated"
    module: str = "laudos"

    laudo_id: int = 0
    processo_id: int = 0
    content: str = ""  # Generated laudo text
    status: str = "draft"  # draft, review, published
    template_used: Optional[str] = None


@dataclass
class LaudoPublished(Event):
    """Emitted when a laudo is published (ready for signature)."""

    event_type: str = "LaudoPublished"
    module: str = "laudos"

    laudo_id: int = 0
    processo_id: int = 0
    docx_path: str = ""  # Path to generated DOCX
    pdf_path: str = ""  # Path to generated PDF


@dataclass
class BoletoSynced(Event):
    """Emitted when boleto status is synced from Inter Bank."""

    event_type: str = "BoletoSynced"
    module: str = "financeiro"

    boleto_id: str = ""  # Boleto number from Inter
    processo_id: int = 0
    status: str = ""  # gerado, pago, vencido, baixado
    valor: float = 0.0
    vencimento: Optional[str] = None  # ISO format date
    pago_em: Optional[str] = None  # ISO format datetime


@dataclass
class ReceitaRecorded(Event):
    """Emitted when receita is recorded in financeiro module."""

    event_type: str = "ReceitaRecorded"
    module: str = "financeiro"

    receita_id: int = 0
    processo_id: int = 0
    valor: float = 0.0
    competencia: str = ""  # YYYY-MM format
    descricao: str = ""


@dataclass
class IntimacaoReceived(Event):
    """Emitted when a new intimacao is received via ESAJ."""

    event_type: str = "IntimacaoReceived"
    module: str = "esaj"

    intimacao_id: int = 0
    processo_id: int = 0
    numero_cnj: str = ""  # CNJ process number
    tipo_intimacao: str = ""  # ex: "nova ação", "agravo", "decisão"
    prazo_dias: int = 0
    data_recebimento: str = ""  # ISO format date


@dataclass
class IntimacaoBumped(Event):
    """Emitted when intimacao status changes (e.g., prazo vencido)."""

    event_type: str = "IntimacaoBumped"
    module: str = "esaj"

    intimacao_id: int = 0
    processo_id: int = 0
    anterior_status: str = ""
    novo_status: str = ""  # ex: "ativa" → "vencida"


@dataclass
class AnalysisCompleted(Event):
    """Emitted when IA analysis completes (ia module)."""

    event_type: str = "AnalysisCompleted"
    module: str = "ia"

    analise_id: int = 0
    processo_id: int = 0
    tipo_analise: str = ""  # ex: "classificacao_area", "interpretacao_decisao"
    resultado: Dict[str, Any] = field(default_factory=dict)
    confianca: float = 0.0  # 0.0 - 1.0


# Event type registry for validation
EVENT_TYPES = {
    ProcessoCreated,
    ProcessoUpdated,
    LaudoGenerated,
    LaudoPublished,
    BoletoSynced,
    ReceitaRecorded,
    IntimacaoReceived,
    IntimacaoBumped,
    AnalysisCompleted,
}

# String mapping for deserialization
EVENT_TYPE_MAP = {
    "ProcessoCreated": ProcessoCreated,
    "ProcessoUpdated": ProcessoUpdated,
    "LaudoGenerated": LaudoGenerated,
    "LaudoPublished": LaudoPublished,
    "BoletoSynced": BoletoSynced,
    "ReceitaRecorded": ReceitaRecorded,
    "IntimacaoReceived": IntimacaoReceived,
    "IntimacaoBumped": IntimacaoBumped,
    "AnalysisCompleted": AnalysisCompleted,
}
