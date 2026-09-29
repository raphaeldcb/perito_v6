"""Scheduler automático de busca ESAJ: 6h e 20h UTC diariamente."""
import logging
import threading
import time
import schedule
from datetime import datetime

from app.services.database import SessionLocal
from app.services.esaj_browser_automation import buscar_intimacoes_esaj
import os

logger = logging.getLogger(__name__)

_state = {"running": False, "ultima_execucao": None, "ultima_status": None}


def _job_buscar_esaj():
    """Busca intimações ESAJ automaticamente."""
    logger.info("🔄 Iniciando busca automática ESAJ (20h e 6h)")

    cpf = os.environ.get("CPF_ESAJ", "")
    senha = os.environ.get("SENHA_ESAJ", "")

    if not cpf or not senha:
        logger.warning("⚠️ CPF_ESAJ ou SENHA_ESAJ não configurados")
        return

    try:
        resultado = buscar_intimacoes_esaj(cpf, senha)
        _state["ultima_execucao"] = datetime.utcnow().isoformat()
        _state["ultima_status"] = resultado.get("status", "desconhecido")
        logger.info(f"✅ Busca ESAJ concluída: {resultado}")
    except Exception as e:
        logger.error(f"❌ Erro busca ESAJ: {e}")
        _state["ultima_status"] = f"erro: {str(e)}"


def _scheduler_thread():
    """Thread daemon que executa busca ESAJ às 6h e 20h UTC."""
    # Horários fixos: 6:00 UTC e 20:00 UTC
    schedule.every().day.at("06:00").do(_job_buscar_esaj)
    schedule.every().day.at("20:00").do(_job_buscar_esaj)

    logger.info("✅ Scheduler ESAJ iniciado (06:00 e 20:00 UTC)")
    _state["running"] = True

    while _state["running"]:
        schedule.run_pending()
        time.sleep(60)


def iniciar_scheduler_esaj():
    """Inicia o scheduler em thread daemon."""
    if not os.environ.get("ESAJ_BUSCA_AUTOMATICA", "1") == "1":
        logger.info("⏸️ Busca ESAJ desabilitada (ESAJ_BUSCA_AUTOMATICA=0)")
        return

    thread = threading.Thread(target=_scheduler_thread, daemon=True)
    thread.start()
    logger.info("✅ Thread ESAJ iniciada (6h e 20h UTC)")


def obter_estado():
    """Retorna estado do scheduler."""
    return _state.copy()
