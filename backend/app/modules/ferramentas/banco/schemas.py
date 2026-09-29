"""Banco Module — Pydantic schemas for banking operations.

Consolidates schemas from:
- v6/backend/app/routes/inter_banco.py
- v6/backend/app/routes/inter_api.py
- v6/backend/app/routes/tjms.py
"""
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# INTER OAUTH & ACCOUNT
# ============================================================================

class InterConnectRequest(BaseModel):
    """Request para conectar conta do Inter (OAuth callback)."""
    authorization_code: str  # Código do OAuth (Bruno faz login Inter)


# ============================================================================
# INTER SALDO & EXTRATO
# ============================================================================

class ExtratoBuscaRequest(BaseModel):
    """Request para consulta de extrato com período."""
    data_inicio: str  # YYYY-MM-DD
    data_fim: str  # YYYY-MM-DD


# ============================================================================
# INTER BOLETOS
# ============================================================================

class BoletoEmitirRequest(BaseModel):
    """Request para emissão de boleto no Inter."""
    valor: float
    vencimento: str  # YYYY-MM-DD
    descricao: str
    nome_beneficiario: str
    cpf_cnpj_beneficiario: str
    pix_com_qrcode: bool = False


# ============================================================================
# PIX TRANSFERS
# ============================================================================

class PixTransferRequest(BaseModel):
    """Request para transferência PIX."""
    chave_destino: str = Field(
        ...,
        description="CPF, email, telefone ou chave aleatória"
    )
    valor_centavos: int = Field(
        ...,
        gt=0,
        description="Valor em centavos (100000 = R$ 1.000,00)"
    )
    descricao: str = Field(..., max_length=100)
    coletador_id: Optional[int] = Field(None, description="Se é pagamento a coletador")
    processo_id: Optional[int] = Field(None, description="Se é pagamento relacionado a processo")


# ============================================================================
# WEBHOOKS
# ============================================================================

class WebhookPagamentoConfirmado(BaseModel):
    """Webhook do Banco Inter — pagamento confirmado."""
    transaction_id: str
    status: str  # "APPROVED", "DECLINED", etc
    valor: int  # centavos
    data_confirmacao: str  # ISO8601
    motivo_rejeicao: Optional[str] = None


# ============================================================================
# TJMS DOCUMENT DOWNLOAD
# ============================================================================

class DownloadRequest(BaseModel):
    """Request para download de autos TJMS."""
    cnj: str  # Número CNJ do processo
