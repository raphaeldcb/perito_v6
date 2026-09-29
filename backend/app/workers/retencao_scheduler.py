"""Scheduler de retenção de arquivos (1º dia do mês, 02:00 UTC)."""
import logging
import threading
import time
from datetime import datetime

import schedule

from app.services.database import SessionLocal
from app.services.retencao_arquivos import arquivar_documentos_antigos

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


def _job_arquivar_antigos():
    """Arquiva documentos com > 5 anos."""
    logger.info("Iniciando arquivamento de documentos antigos")
    db = SessionLocal()
    try:
        resultado = arquivar_documentos_antigos(db)
        _scheduler_state["ultima_execucao"] = datetime.utcnow().isoformat()
        _scheduler_state["ultima_status"] = "ok"
        _scheduler_state["total_execucoes"] += 1
        logger.info(f"✅ Arquivamento concluído: {resultado}")
    except Exception as e:
        logger.error(f"❌ Falha no arquivamento: {e}", exc_info=True)
        _scheduler_state["total_erros"] += 1
        _scheduler_state["ultima_status"] = "error"
    finally:
        db.close()


def _scheduler_thread():
    """Thread daemon que executa jobs agendados."""
    # Executa todo dia às 02:00 UTC (verifica internamente se é 1º dia do mês)
    schedule.every().day.at("02:00").do(_job_arquivar_antigos)

    logger.info("Scheduler de retenção iniciado (1º dia do mês, 02:00 UTC)")
    _scheduler_state["running"] = True

    while _scheduler_state["running"]:
        schedule.run_pending()
        time.sleep(60)


def iniciar_scheduler_retencao():
    """Inicia o scheduler em thread daemon."""
    thread = threading.Thread(target=_scheduler_thread, daemon=True)
    thread.start()
    logger.info("✅ Thread de retenção iniciada")
