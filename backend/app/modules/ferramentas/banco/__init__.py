"""Banco Module — Banking integrations (Inter, TJMS).

Consolidates banking operations including:
- Inter OAuth & account management
- Balance & statement inquiries
- PIX transfers
- Boleto issuance (stub)
- Webhook handlers
- TJMS document downloads
"""
from .router import router
from .schemas import (
    InterConnectRequest,
    ExtratoBuscaRequest,
    BoletoEmitirRequest,
    PixTransferRequest,
    WebhookPagamentoConfirmado,
    DownloadRequest,
)

__all__ = [
    "router",
    "InterConnectRequest",
    "ExtratoBuscaRequest",
    "BoletoEmitirRequest",
    "PixTransferRequest",
    "WebhookPagamentoConfirmado",
    "DownloadRequest",
]
