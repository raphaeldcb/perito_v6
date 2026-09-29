"""
Conta Única service — Integration with Conta Única payment system.

Synchronizes payments received via Conta Única with local boleto records.
Provides data reconciliation and status tracking.
"""

import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import httpx

from app.modules.financeiro.models import Boleto, BoletoStatus
from app.modules.financeiro.repositories import BoletoRepository
from app.shared.exceptions import ExternalServiceException, ValidationException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ContaUnicaService:
    """Service for managing Conta Única payment synchronization."""

    def __init__(self, db: Session, repository: BoletoRepository):
        """Initialize Conta Única service."""
        self.db = db
        self.repository = repository
        self.conta_unica_api_url = "https://api.contaunica.gov.br"
        self.timeout = 10  # seconds

    async def sync_payments(self) -> Dict[str, Any]:
        """
        Sync all pending payments from Conta Única.

        This method queries the Conta Única API for any payments received
        and updates corresponding boleto records in the system.

        Returns:
            Dictionary with sync results:
            {
                "synced": number of boletos updated,
                "total": number of payments found,
                "errors": number of errors,
                "timestamp": sync timestamp
            }

        Raises:
            ExternalServiceException: If API call fails
        """
        try:
            # Get all pending boletos
            pending_boletos = await self.repository.get_by_status(BoletoStatus.EMITIDO)

            if not pending_boletos:
                logger.info("Nenhum boleto pendente para sincronizar com Conta Única")
                return {
                    "synced": 0,
                    "total": 0,
                    "errors": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Query Conta Única for payments
            payments = await self._fetch_payments()

            synced = 0
            errors = 0

            for payment in payments:
                try:
                    # Match payment with boleto
                    boleto = self._find_matching_boleto(payment, pending_boletos)
                    if boleto:
                        # Update boleto
                        boleto.status = BoletoStatus.PAGO
                        boleto.data_pagamento = datetime.fromisoformat(payment.get("data_pagamento"))
                        self.db.commit()
                        synced += 1
                        logger.info(f"Boleto {boleto.id} marcado como pago via Conta Única")
                except Exception as e:
                    errors += 1
                    logger.error(f"Erro ao processar pagamento Conta Única: {str(e)}")

            logger.info(f"Sincronização Conta Única: {synced} boletos atualizados, {errors} erros")

            return {
                "synced": synced,
                "total": len(payments),
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Erro geral na sincronização Conta Única: {str(e)}")
            raise ExternalServiceException(
                f"Erro ao sincronizar pagamentos Conta Única: {str(e)}",
                error_code="CONTA_UNICA_SYNC_ERROR",
            )

    async def get_payment_status(self, boleto_id: int) -> Dict[str, Any]:
        """
        Get payment status from Conta Única for a specific boleto.

        Args:
            boleto_id: ID of boleto to check

        Returns:
            Payment status information

        Raises:
            ValidationException: If boleto not found
            ExternalServiceException: If API call fails
        """
        boleto = await self.repository.get_by_id(boleto_id)
        if not boleto:
            raise ValidationException("Boleto não encontrado", error_code="BOLETO_NOT_FOUND")

        try:
            # Query Conta Única for this boleto
            payments = await self._fetch_payments(numero=boleto.numero)

            if payments:
                payment = payments[0]
                return {
                    "boleto_id": boleto_id,
                    "numero": boleto.numero,
                    "status": "pago" if payment.get("pago") else "pendente",
                    "data_pagamento": payment.get("data_pagamento"),
                    "valor_pago": payment.get("valor"),
                    "forma_pagamento": payment.get("forma_pagamento"),
                }
            else:
                return {
                    "boleto_id": boleto_id,
                    "numero": boleto.numero,
                    "status": "pendente",
                    "data_pagamento": None,
                    "valor_pago": None,
                    "forma_pagamento": None,
                }

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Erro ao consultar status Conta Única: {str(e)}")
            raise ExternalServiceException(
                f"Erro ao consultar status no Conta Única: {str(e)}",
                error_code="CONTA_UNICA_STATUS_ERROR",
            )

    async def _fetch_payments(self, numero: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Internal method to fetch payments from Conta Única API.

        Args:
            numero: Optional boleto number to filter

        Returns:
            List of payment dictionaries

        Raises:
            ExternalServiceException: If API call fails
        """
        import os
        conta_unica_token = os.getenv("CONTA_UNICA_TOKEN", "test-token")

        endpoint = "/payments"
        if numero:
            endpoint += f"?numero={numero}"

        url = f"{self.conta_unica_api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {conta_unica_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json().get("payments", [])
                elif response.status_code == 401:
                    raise ExternalServiceException(
                        "Autenticação Conta Única falhou",
                        error_code="CONTA_UNICA_AUTH_ERROR",
                        status_code=401,
                    )
                elif response.status_code == 404:
                    return []  # No payments found
                else:
                    raise ExternalServiceException(
                        f"Conta Única API error: {response.status_code}",
                        error_code="CONTA_UNICA_API_ERROR",
                        status_code=response.status_code,
                    )

        except httpx.TimeoutException:
            raise ExternalServiceException(
                "Timeout na chamada para Conta Única",
                error_code="CONTA_UNICA_TIMEOUT",
                status_code=504,
            )
        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao chamar Conta Única: {str(e)}")
            raise ExternalServiceException(
                f"Erro inesperado ao chamar Conta Única: {str(e)}",
                error_code="CONTA_UNICA_UNEXPECTED_ERROR",
            )

    def _find_matching_boleto(
        self,
        payment: Dict[str, Any],
        boletos: List[Boleto],
    ) -> Optional[Boleto]:
        """
        Find a boleto matching a payment record.

        Uses simple matching strategy: compares boleto numero with payment numero.

        Args:
            payment: Payment data from Conta Única
            boletos: List of local boletos to search

        Returns:
            Matching Boleto or None
        """
        payment_numero = payment.get("numero", "")

        for boleto in boletos:
            if boleto.numero == payment_numero:
                # Verify amount matches (within tolerance)
                payment_valor = float(payment.get("valor", 0))
                boleto_valor = float(boleto.valor)

                # Allow 1% tolerance due to fees/adjustments
                tolerance = boleto_valor * 0.01
                if abs(payment_valor - boleto_valor) <= tolerance:
                    return boleto

        return None


__all__ = ["ContaUnicaService"]
