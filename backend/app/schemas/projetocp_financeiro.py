"""
Pydantic schemas for ProjetoCP Phase 2 Financeiro (input/output validation)
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class FinanceiroTipo(str, Enum):
    HONORARIO_LAUDO = "honorario_laudo"
    HONORARIO_SUCUMBENCIA = "honorario_sucumbencia"
    CUSTAS_JUDICIAIS = "custas_judiciais"
    REEMBOLSO_DESPESA = "reembolso_despesa"
    COMISSAO_BANCA = "comissao_banca"
    MULTA_CONTRACTUAL = "multa_contractual"


class FinanceiroStatus(str, Enum):
    PENDENTE = "pendente"
    VENCIDO = "vencido"
    EM_COBRANCA = "em_cobranca"
    PARCIALMENTE_PAGO = "parcialmente_pago"
    PAGO = "pago"
    CANCELADO = "cancelado"
    PRESCRITO = "prescrito"


# ============ Financeiro Schemas ============

class FinanceiroCriarRequest(BaseModel):
    processo_id: int
    laudo_id: Optional[int] = None
    tipo: FinanceiroTipo
    descricao: Optional[str] = None
    valor_bruto: Decimal = Field(gt=0)
    valor_desconto: Decimal = Field(default=Decimal(0), ge=0)
    moeda: str = "BRL"
    data_vencimento: datetime
    indexador: str = "SELIC"
    juros_mora_percentual: Decimal = Field(default=Decimal(1.0), ge=0)
    numero_nfse: Optional[str] = None
    numero_rps: Optional[str] = None
    referencia_externa: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator("valor_desconto")
    def validate_desconto(cls, v, values):
        if "valor_bruto" in values and v > values["valor_bruto"]:
            raise ValueError("Desconto não pode ser maior que valor bruto")
        return v

    class Config:
        from_attributes = True


class FinanceiroAtualizarRequest(BaseModel):
    descricao: Optional[str] = None
    valor_bruto: Optional[Decimal] = None
    valor_desconto: Optional[Decimal] = None
    status: Optional[FinanceiroStatus] = None
    motivo_cancelamento: Optional[str] = None
    data_vencimento: Optional[datetime] = None
    indexador: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class FinanceiroResponse(BaseModel):
    id: int
    processo_id: int
    laudo_id: Optional[int]
    tipo: str
    descricao: Optional[str]
    valor_bruto: Decimal
    valor_desconto: Decimal
    valor_liquido: Decimal
    moeda: str
    data_emissao: datetime
    data_vencimento: datetime
    data_recebimento_prevista: Optional[datetime]
    data_primeiro_recebimento: Optional[datetime]
    indexador: str
    juros_mora_percentual: Decimal
    status: str
    numero_nfse: Optional[str]
    numero_rps: Optional[str]
    referencia_externa: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Pagamento Schemas ============

class PagamentoCriarRequest(BaseModel):
    financeiro_id: int
    valor_recebido: Decimal = Field(gt=0)
    metodo_pagamento: str
    banco_recebimento: Optional[str] = None
    referencia_banco: Optional[str] = None
    comprovante_path: Optional[str] = None
    nota: Optional[str] = None
    data_pagamento: Optional[datetime] = None

    class Config:
        from_attributes = True


class PagamentoResponse(BaseModel):
    id: int
    financeiro_id: int
    parcela_numero: int
    data_pagamento: datetime
    data_comprovacao: Optional[datetime]
    valor_recebido: Decimal
    metodo_pagamento: str
    banco_recebimento: Optional[str]
    referencia_banco: Optional[str]
    comprovante_path: Optional[str]
    em_custódia: bool
    custódia_motivo: Optional[str]
    reconciliado: bool
    nota: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ ParcelaFinanceira Schemas ============

class ParcelaFinanceiraCriarRequest(BaseModel):
    financeiro_id: int
    numero_parcela: int
    valor_parcela: Decimal = Field(gt=0)
    data_vencimento: datetime
    status: str = "pendente"

    class Config:
        from_attributes = True


class ParcelaFinanceiraResponse(BaseModel):
    id: int
    financeiro_id: int
    numero_parcela: int
    valor_parcela: Decimal
    data_vencimento: datetime
    data_pagamento_efetivo: Optional[datetime]
    status: str
    juros_calculados: Decimal
    multa_atraso: Decimal
    pagamento_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Parcelamento Automático ============

class ParcelamentoRequest(BaseModel):
    financeiro_id: int
    num_parcelas: int = Field(ge=1, le=12)
    data_primeira_parcela: Optional[datetime] = None
    dias_entre_parcelas: int = 30

    class Config:
        from_attributes = True


class ParcelamentoResponse(BaseModel):
    financeiro_id: int
    total_parcelas: int
    parcelas: List[ParcelaFinanceiraResponse]
    valor_total: Decimal

    class Config:
        from_attributes = True


# ============ FinanceiroConfiguracao Schemas ============

class FinanceiroConfiguracaoResponse(BaseModel):
    id: int
    juros_mora_percentual: Decimal
    multa_atraso_percentual: Decimal
    dias_tolerancia_atraso: int
    ativa_parcelamento_automatico: bool
    num_parcelas_padrao: int
    dias_entre_parcelas: int
    indexador_padrao: str
    dias_antes_vencer_alerta: int
    dias_apos_vencer_notificacao: int
    ativa_cobranca_automatica: bool
    max_tentativas_cobranca: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinanceiroConfiguracaoAtualizar(BaseModel):
    juros_mora_percentual: Optional[Decimal] = None
    multa_atraso_percentual: Optional[Decimal] = None
    dias_tolerancia_atraso: Optional[int] = None
    ativa_parcelamento_automatico: Optional[bool] = None
    num_parcelas_padrao: Optional[int] = None
    dias_entre_parcelas: Optional[int] = None
    indexador_padrao: Optional[str] = None
    dias_antes_vencer_alerta: Optional[int] = None
    dias_apos_vencer_notificacao: Optional[int] = None
    ativa_cobranca_automatica: Optional[bool] = None
    max_tentativas_cobranca: Optional[int] = None

    class Config:
        from_attributes = True


# ============ Dashboard/Stats Schemas ============

class FinanceiroStatsResponse(BaseModel):
    total_emitido: Decimal  # Soma de valor_bruto
    total_recebido: Decimal  # Soma de pagamentos
    total_pendente: Decimal  # Emitido - recebido
    total_vencido: Decimal  # Vencido mas não pago
    taxa_recebimento: Decimal  # % recebido
    quantidade_processos: int
    quantidade_lancamentos: int
    quantidade_vencidos: int
    quantidade_abertos: int

    class Config:
        from_attributes = True


class FinanceiroRelatorioResponse(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    stats: FinanceiroStatsResponse
    lancamentos_por_status: Dict[str, int]
    lancamentos_por_tipo: Dict[str, Decimal]
    pagamentos_por_metodo: Dict[str, Decimal]
    faturamento_por_area: Dict[str, Decimal]

    class Config:
        from_attributes = True


# ============ Cobrança ============

class CobrancaIniciarRequest(BaseModel):
    financeiro_id: int
    tipo_notificacao: str = "email"  # email, whatsapp, cartorio
    dias_atraso_minimo: int = 3
    enviar_para: Optional[str] = None

    class Config:
        from_attributes = True


class CobrancaResponse(BaseModel):
    financeiro_id: int
    status: str
    proxima_tentativa: Optional[datetime]
    ultimo_envio: Optional[datetime]
    tentativa_numero: int
    mensagem: str

    class Config:
        from_attributes = True


# ============ Conciliação ============

class ConciliacaoPagamentoRequest(BaseModel):
    pagamento_id: int
    lancamento_bancario_id: int  # Do módulo de conciliação

    class Config:
        from_attributes = True


class ConciliacaoResponse(BaseModel):
    pagamento_id: int
    lancamento_bancario_id: int
    data_reconciliacao: datetime
    status: str
    valor_diferenca: Optional[Decimal]

    class Config:
        from_attributes = True
