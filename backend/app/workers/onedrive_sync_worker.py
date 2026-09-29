"""Worker de agendamento para sincronização OneDrive.

Executa sincronização de templates diariamente (ou sob demanda).
Mantém log de execuções em memória para dashboard de status.
"""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

import schedule

from app.services.onedrive_sync import configurado, sincronizar_modelos

logger = logging.getLogger(__name__)

# Estado global do scheduler
_scheduler_state = {
    "running": False,
    "ultima_sync": None,
    "ultima_sync_status": None,
    "proxima_sync": None,
    "total_execucoes": 0,
    "total_erros": 0,
}


def obter_estado_scheduler() -> dict:
    """Retorna estado atual do scheduler."""
    return _scheduler_state.copy()


def _job_sync_wrapper():
    """Wrapper que executa o sync e rastreia estado."""
    logger.info("=" * 60)
    logger.info("Iniciando job de sincronização OneDrive agendado")
    logger.info("=" * 60)

    try:
        if not configurado():
            logger.warning("OneDrive sync desabilitado: credenciais não configuradas")
            return

        resultado = sincronizar_modelos()

        _scheduler_state["ultima_sync"] = datetime.utcnow().isoformat()
        _scheduler_state["ultima_sync_status"] = resultado.get("status", "unknown")
        _scheduler_state["total_execucoes"] += 1

        logger.info(
            f"✅ Sync concluído: "
            f"{resultado.get('criados', 0)} criados, "
            f"{resultado.get('atualizados', 0)} atualizados, "
            f"{resultado.get('erros', 0)} erros"
        )

        if resultado.get("erros", 0) > 0:
            logger.warning(f"Erros detectados: {resultado.get('erros_detalhes', [])}")

    except Exception as e:
        logger.error(f"❌ Falha no job de sync: {e}", exc_info=True)
        _scheduler_state["total_erros"] += 1
        _scheduler_state["ultima_sync_status"] = "error"


def _schedule_job():
    """Configura o job de agendamento."""
    intervalo = os.getenv("ONEDRIVE_SYNC_INTERVAL", "daily")
    hora_sync = os.getenv("ONEDRIVE_SYNC_HOUR", "02:00")

    if intervalo == "daily":
        logger.info(f"Agendando sync diário às {hora_sync} UTC")
        schedule.every().day.at(hora_sync).do(_job_sync_wrapper)
    elif intervalo == "hourly":
        logger.info("Agendando sync a cada hora")
        schedule.every().hour.do(_job_sync_wrapper)
    elif intervalo == "never":
        logger.info("Sync agendado desabilitado (ONEDRIVE_SYNC_INTERVAL=never)")
        return
    else:
        logger.warning(f"Intervalo desconhecido: {intervalo}, usando daily")
        schedule.every().day.at(hora_sync).do(_job_sync_wrapper)

    # Calcula próxima execução
    if hasattr(schedule, 'idle_seconds'):
        segundos = schedule.idle_seconds()
        if segundos:
            proxima = datetime.utcnow()
            proxima_sync_time = datetime.fromtimestamp(
                proxima.timestamp() + segundos
            )
            _scheduler_state["proxima_sync"] = proxima_sync_time.isoformat()


def _run_scheduler_loop():
    """Loop que executa jobs agendados."""
    logger.info("Scheduler de OneDrive sync iniciado (thread daemon)")

    _schedule_job()

    while True:
        try:
            # Executa jobs pendentes
            schedule.run_pending()

            # Aguarda antes de próxima verificação
            time.sleep(60)

        except Exception as e:
            logger.error(f"Erro no scheduler loop: {e}", exc_info=True)
            time.sleep(60)


def iniciar_scheduler_onedrive():
    """Inicia o scheduler em thread daemon."""
    if not configurado():
        logger.info("OneDrive sync skipped: credenciais não configuradas")
        return

    if _scheduler_state["running"]:
        logger.warning("Scheduler já está em execução")
        return

    _scheduler_state["running"] = True

    thread = threading.Thread(target=_run_scheduler_loop, daemon=True, name="OneDriveSync")
    thread.start()

    logger.info("✅ OneDrive sync scheduler iniciado")


def executar_sync_agora():
    """Força uma sincronização imediata (admin endpoint)."""
    logger.info("Sincronização sob demanda solicitada via API")
    _job_sync_wrapper()
    return obter_estado_scheduler()
