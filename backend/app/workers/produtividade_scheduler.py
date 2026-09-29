"""Worker de agendamento: agrega custos AssistProduction todo dia de madrugada.

Segue o mesmo padrão do onedrive_sync_worker.py (thread daemon + lib `schedule`)
— este projeto não usa Celery, e não vale a pena subir broker/worker separados
para um job diário de agregação. Se o volume de eventos crescer para
justificar processamento distribuído, aí sim migra para Celery/RQ.
"""
import logging
import os
import threading
import time
from datetime import date, datetime, timedelta

import schedule

from app.services.database import SessionLocal
from app.services.produtividade_financeiro import agregar_dia
from app.services.produtividade_qwen import detectar_e_enfileirar_suspeitos

logger = logging.getLogger(__name__)

_scheduler_state = {
    "running": False,
    "ultima_agregacao": None,
    "ultima_agregacao_status": None,
    "total_execucoes": 0,
    "total_erros": 0,
}


def obter_estado_scheduler() -> dict:
    return _scheduler_state.copy()


def _job_agregar_wrapper():
    """Agrega o dia anterior (D-1) — dá tempo do agente AssistProduction
    terminar de enviar os últimos eventos do dia antes de fechar a conta."""
    ontem = date.today() - timedelta(days=1)
    logger.info(f"Iniciando agregação AssistProduction financeiro para {ontem.isoformat()}")
    db = SessionLocal()
    try:
        resultado = agregar_dia(db, ontem)
        # Suspeitos (heurística já rodou implicitamente: classifica no momento
        # de enfileirar) -> Job de parecer Qwen, 1x/dia/device, pro mac_agent.
        try:
            n_suspeitos = detectar_e_enfileirar_suspeitos(db, ontem)
            if n_suspeitos:
                resultado["analises_qwen_enfileiradas"] = n_suspeitos
        except Exception:
            logger.exception("Falha ao enfileirar análise Qwen de produtividade")
        _scheduler_state["ultima_agregacao"] = datetime.utcnow().isoformat()
        _scheduler_state["ultima_agregacao_status"] = "ok"
        _scheduler_state["total_execucoes"] += 1
        logger.info(f"✅ Agregação concluída: {resultado}")
    except Exception as e:
        logger.error(f"❌ Falha na agregação AssistProduction: {e}", exc_info=True)
        _scheduler_state["total_erros"] += 1
        _scheduler_state["ultima_agregacao_status"] = "error"
    finally:
        db.close()


def _run_scheduler_loop():
    hora = os.getenv("PRODUTIVIDADE_SYNC_HOUR", "01:00")
    logger.info(f"Scheduler de agregação AssistProduction iniciado (thread daemon) — diário às {hora} UTC")
    schedule.every().day.at(hora).do(_job_agregar_wrapper)

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Erro no scheduler loop de produtividade: {e}", exc_info=True)
            time.sleep(60)


def iniciar_scheduler_produtividade():
    if _scheduler_state["running"]:
        logger.warning("Scheduler de produtividade já está em execução")
        return
    _scheduler_state["running"] = True
    thread = threading.Thread(target=_run_scheduler_loop, daemon=True, name="ProdutividadeFinanceiroSync")
    thread.start()
    logger.info("✅ Scheduler de agregação AssistProduction iniciado")


def executar_agregacao_agora(data_ref: date | None = None) -> dict:
    """Força agregação imediata (admin endpoint / backfill)."""
    db = SessionLocal()
    try:
        alvo = data_ref or (date.today() - timedelta(days=1))
        resultado = agregar_dia(db, alvo)
        try:
            n = detectar_e_enfileirar_suspeitos(db, alvo)
            if n:
                resultado["analises_qwen_enfileiradas"] = n
        except Exception:
            logger.exception("Falha ao enfileirar análise Qwen de produtividade (manual)")
        return resultado
    finally:
        db.close()
