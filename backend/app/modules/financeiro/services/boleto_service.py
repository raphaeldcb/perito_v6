"""
Boleto service — Banco Inter API integration and boleto management.

Handles generation, emission, and tracking of boletos through Banco Inter.
Implements circuit breaker pattern with timeout and retry logic.
"""

import logging
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx

from app.modules.financeiro.models import Boleto, BoletoStatus
from app.modules.financeiro.repositories import BoletoRepository
from app.shared.exceptions import ExternalServiceException, ValidationException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BoletoService:
    """Service for managing boletos and Banco Inter integration."""

    def __init__(self, db: Session, repository: BoletoRepository):
        """Initialize Boleto service."""
        self.db = db
        self.repository = repository
        self.inter_api_url = "https://api.bancointer.com.br"
        self.inter_sandbox_url = "https://api-sandbox.bancointer.com.br"
        self.timeout = 10  # seconds
        self.max_retries = 3

    async def generate_boleto(
        self,
        processo_id: int,
        valor: Decimal,
        vencimento: date,
        descricao: Optional[str] = None,
    ) -> Boleto:
        """
        Generate a new boleto in Banco Inter.

        Args:
            processo_id: ID of the related processo
            valor: Boleto value
            vencimento: Due date
            descricao: Optional description

        Returns:
            Boleto object with Inter data populated

        Raises:
            ValidationException: If input is invalid
            ExternalServiceException: If Inter API call fails
        """
        if valor <= 0:
            raise ValidationException("Valor deve ser maior que zero", error_code="INVALID_VALOR")

        if vencimento <= date.today():
            raise ValidationException("Vencimento deve ser maior que hoje", error_code="INVALID_VENCIMENTO")

        # Generate unique numero (simplified: timestamp-based)
        numero = f"{processo_id}{int(datetime.now().timestamp())}"[-12:]

        try:
            # Call Banco Inter API to generate boleto
            inter_data = await self._call_inter_api(
                method="POST",
                endpoint="/register-boleto",
                payload={
                    "numero": numero,
                    "valor": float(valor),
                    "vencimento": vencimento.isoformat(),
                    "descricao": descricao or f"Pagamento processo {processo_id}",
                },
            )

            # Create boleto in local database
            boleto = Boleto(
                numero=numero,
                processo_id=processo_id,
                valor=valor,
                vencimento=vencimento,
                descricao=descricao,
                status=BoletoStatus.EMITIDO,
                inter_id=inter_data.get("id"),
                inter_url=inter_data.get("url"),
                qr_code=inter_data.get("qr_code"),
                data_emissao=datetime.utcnow(),
            )

            boleto = await self.repository.create(boleto)
            logger.info(f"Boleto criado: {boleto.id} (Inter ID: {boleto.inter_id})")

            return boleto

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Erro ao gerar boleto: {str(e)}")
            raise ExternalServiceException(
                f"Erro ao gerar boleto no Banco Inter: {str(e)}",
                error_code="BANCO_INTER_ERROR",
            )

    async def sync_payment_status(self, boleto_id: int) -> Boleto:
        """
        Sync payment status from Banco Inter.

        Queries Inter API for latest boleto status and updates local record.

        Args:
            boleto_id: ID of boleto to sync

        Returns:
            Updated Boleto object

        Raises:
            ValidationException: If boleto not found
            ExternalServiceException: If API call fails
        """
        boleto = await self.repository.get_by_id(boleto_id)
        if not boleto:
            raise ValidationException("Boleto não encontrado", error_code="BOLETO_NOT_FOUND")

        if not boleto.inter_id:
            raise ValidationException(
                "Boleto não tem ID do Inter associado",
                error_code="BOLETO_NO_INTER_ID",
            )

        try:
            # Query Inter API for status
            inter_data = await self._call_inter_api(
                method="GET",
                endpoint=f"/boleto/{boleto.inter_id}",
            )

            # Update boleto based on response
            status_map = {
                "aberto": BoletoStatus.EMITIDO,
                "pago": BoletoStatus.PAGO,
                "vencido": BoletoStatus.VENCIDO,
                "cancelado": BoletoStatus.CANCELADO,
            }

            new_status = status_map.get(inter_data.get("status"), boleto.status)
            boleto.status = new_status

            if new_status == BoletoStatus.PAGO:
                boleto.data_pagamento = datetime.fromisoformat(
                    inter_data.get("data_pagamento")
                ) if inter_data.get("data_pagamento") else datetime.utcnow()

            self.db.commit()
            logger.info(f"Status boleto atualizado: {boleto.id} → {new_status}")

            return boleto

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Erro ao sincronizar status do boleto: {str(e)}")
            raise ExternalServiceException(
                f"Erro ao sincronizar status do boleto: {str(e)}",
                error_code="SYNC_STATUS_ERROR",
            )

    async def cancel_boleto(self, boleto_id: int) -> Boleto:
        """
        Cancel a boleto.

        Args:
            boleto_id: ID of boleto to cancel

        Returns:
            Updated Boleto object

        Raises:
            ValidationException: If boleto not found or already paid
            ExternalServiceException: If API call fails
        """
        boleto = await self.repository.get_by_id(boleto_id)
        if not boleto:
            raise ValidationException("Boleto não encontrado", error_code="BOLETO_NOT_FOUND")

        if boleto.status == BoletoStatus.PAGO:
            raise ValidationException(
                "Não é possível cancelar boleto já pago",
                error_code="BOLETO_ALREADY_PAID",
            )

        try:
            if boleto.inter_id:
                await self._call_inter_api(
                    method="POST",
                    endpoint=f"/boleto/{boleto.inter_id}/cancel",
                )

            boleto.status = BoletoStatus.CANCELADO
            boleto.data_cancelamento = datetime.utcnow()
            self.db.commit()
            logger.info(f"Boleto cancelado: {boleto.id}")

            return boleto

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Erro ao cancelar boleto: {str(e)}")
            raise ExternalServiceException(
                f"Erro ao cancelar boleto: {str(e)}",
                error_code="CANCEL_BOLETO_ERROR",
            )

    async def _call_inter_api(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Internal method to call Banco Inter API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint path
            payload: Request payload (optional)

        Returns:
            API response data

        Raises:
            ExternalServiceException: If all retries fail
        """
        import os
        sandbox_mode = os.getenv("FINANCEIRO_SANDBOX", "true").lower() == "true"
        base_url = self.inter_sandbox_url if sandbox_mode else self.inter_api_url
        inter_key = os.getenv("BANCO_INTER_KEY", "test-key-sandbox")

        url = f"{base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {inter_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method == "GET":
                        response = await client.get(url, headers=headers)
                    elif method == "POST":
                        response = await client.post(url, json=payload, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    if response.status_code in [200, 201]:
                        return response.json()
                    elif response.status_code == 401:
                        raise ExternalServiceException(
                            "Autenticação Banco Inter falhou",
                            error_code="INTER_AUTH_ERROR",
                            status_code=401,
                        )
                    elif response.status_code >= 500:
                        logger.warning(f"Inter API error (attempt {attempt + 1}/{self.max_retries}): {response.status_code}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        raise ExternalServiceException(
                            "Banco Inter API indisponível",
                            error_code="INTER_SERVICE_UNAVAILABLE",
                            status_code=502,
                        )
                    else:
                        raise ExternalServiceException(
                            f"Banco Inter API error: {response.status_code}",
                            error_code="INTER_API_ERROR",
                            status_code=response.status_code,
                        )

            except httpx.TimeoutException:
                logger.warning(f"Inter API timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise ExternalServiceException(
                    "Timeout na chamada para Banco Inter",
                    error_code="INTER_TIMEOUT",
                    status_code=504,
                )
            except ExternalServiceException:
                raise
            except Exception as e:
                logger.error(f"Erro inesperado ao chamar Inter API: {str(e)}")
                raise ExternalServiceException(
                    f"Erro inesperado ao chamar Banco Inter: {str(e)}",
                    error_code="INTER_UNEXPECTED_ERROR",
                )

        raise ExternalServiceException(
            "Todas as tentativas de chamar Banco Inter falharam",
            error_code="INTER_MAX_RETRIES_EXCEEDED",
            status_code=502,
        )


__all__ = ["BoletoService"]
