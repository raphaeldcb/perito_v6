"""
Event handlers for ESAJ module.

Handles:
- IntimacaoReceived: New intimacao from eSAJ
- IntimacaoBumped: Intimacao status changes
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def handle_intimacao_received(payload: Dict[str, Any]):
    """
    Handle IntimacaoReceived event.

    Called when new intimacao is received from eSAJ.

    Args:
        payload: Event payload with intimacao_id, processo_id, tipo, prazo, etc.
    """
    try:
        intimacao_id = payload.get("intimacao_id")
        processo_id = payload.get("processo_id")
        tipo = payload.get("tipo_intimacao")
        prazo = payload.get("prazo_dias")

        logger.info(
            f"Processing IntimacaoReceived: {intimacao_id} ({tipo}, prazo {prazo}d, "
            f"Processo: {processo_id})"
        )

        # TODO: Implement workflow
        # - Store intimacao in database
        # - Bind to processo if not already linked
        # - Set prazo alarm (notify at prazo -7, -3, -1 days)
        # - Update processo status to 'urgente' if priority

        logger.info(f"IntimacaoReceived handled: {intimacao_id}")

    except Exception as e:
        logger.error(f"Error handling IntimacaoReceived: {e}", exc_info=True)
        raise


async def handle_intimacao_bumped(payload: Dict[str, Any]):
    """
    Handle IntimacaoBumped event.

    Called when intimacao status changes (e.g., prazo vencido).

    Args:
        payload: Event payload with intimacao_id, anterior_status, novo_status, etc.
    """
    try:
        intimacao_id = payload.get("intimacao_id")
        processo_id = payload.get("processo_id")
        novo_status = payload.get("novo_status")

        logger.info(
            f"Processing IntimacaoBumped: {intimacao_id} → {novo_status} "
            f"(Processo: {processo_id})"
        )

        # TODO: Implement workflow
        # - Update intimacao status in database
        # - If 'vencida', send alert to legal team
        # - Update processo status if needed
        # - Trigger follow-up actions (defesa, moção, etc.)

        logger.info(f"IntimacaoBumped handled: {intimacao_id}")

    except Exception as e:
        logger.error(f"Error handling IntimacaoBumped: {e}", exc_info=True)
        raise
