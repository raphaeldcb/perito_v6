"""Scheduler para monitoramento de comunicações via Microsoft Graph.

Executa a cada 5 minutos para buscar emails não-lidos, classificar como judicial
e armazenar no banco de dados.
"""

import logging
import threading
import time
from datetime import datetime

from app.services.database import SessionLocal
from app.workers.monitor_comunicacoes import processar_caixa_entrada

logger = logging.getLogger(__name__)

_SCHEDULER_THREAD = None
_SCHEDULER_RUNNING = False


def inicializar_scheduler(intervalo_segundos: int = 300):
    """Inicia scheduler de comunicações (padrão: 5 minutos)."""
    global _SCHEDULER_THREAD, _SCHEDULER_RUNNING

    if _SCHEDULER_RUNNING:
        logger.warning("Scheduler de comunicações já está rodando")
        return

    _SCHEDULER_RUNNING = True
    _SCHEDULER_THREAD = threading.Thread(
        target=_loop_scheduler,
        args=(intervalo_segundos,),
        daemon=True,
        name="ComunicacoesScheduler",
    )
    _SCHEDULER_THREAD.start()
    logger.info(f"✅ Scheduler de comunicações iniciado (intervalo: {intervalo_segundos}s)")


def parar_scheduler():
    """Para o scheduler de comunicações."""
    global _SCHEDULER_RUNNING
    _SCHEDULER_RUNNING = False
    logger.info("Scheduler de comunicações parado")


def _loop_scheduler(intervalo: int):
    """Loop principal do scheduler."""
    while _SCHEDULER_RUNNING:
        try:
            logger.debug(f"Executando monitoramento de comunicações em {datetime.now().isoformat()}")
            stats = processar_caixa_entrada(limite=50)
            if stats and stats.get("emails_processados", 0) > 0:
                logger.info(f"📧 Comunicações: {stats['emails_processados']} processados, "
                           f"{stats['judiciais']} judiciais, {stats['erros']} erros")
        except Exception as e:
            logger.error(f"Erro no scheduler de comunicações: {e}", exc_info=True)

        # Aguarda intervalo
        time.sleep(intervalo)


__all__ = ["inicializar_scheduler", "parar_scheduler"]
