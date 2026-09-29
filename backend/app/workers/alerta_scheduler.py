"""Scheduler de alertas de laudo/ofício (06:00 UTC diário)."""
import logging
import threading
import time
from datetime import datetime

import schedule

from app.services.database import SessionLocal
from app.services.alerta_cron import verificar_e_atualizar_alertas

logger = logging.getLogger(__name__)

_scheduler_state = {
    "running": False,
    "ultima_execucao": None,
    "ultima_status": None,
    "total_execucoes": 0,
    "total_erros": 0,
}


def obter_estado_scheduler() -> dict:
    return _scheduler_state.copy()


def _job_verificar_alertas():
    """Verifica alertas de laudo/ofício e envia emails."""
    logger.info("Iniciando verificação de alertas")
    db = SessionLocal()
    try:
        resultado = verificar_e_atualizar_alertas(db)
        _scheduler_state["ultima_execucao"] = datetime.utcnow().isoformat()
        _scheduler_state["ultima_status"] = "ok"
        _scheduler_state["total_execucoes"] += 1
        logger.info(f"✅ Verificação de alertas concluída: {resultado}")
    except Exception as e:
        logger.error(f"❌ Falha na verificação de alertas: {e}", exc_info=True)
        _scheduler_state["total_erros"] += 1
        _scheduler_state["ultima_status"] = "error"
    finally:
        db.close()


def _scheduler_thread():
    """Thread daemon que executa jobs agendados."""
    schedule.every().day.at("06:00").do(_job_verificar_alertas)

    logger.info("Scheduler de alertas iniciado (06:00 UTC)")
    _scheduler_state["running"] = True

    while _scheduler_state["running"]:
        schedule.run_pending()
        time.sleep(60)


def iniciar_scheduler_alertas():
    """Inicia o scheduler em thread daemon."""
    thread = threading.Thread(target=_scheduler_thread, daemon=True)
    thread.start()
    logger.info("✅ Thread de alertas iniciada")
