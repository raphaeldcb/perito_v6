"""Worker de agendamento: dispara deploy_approved_feedback() diariamente às
19h UTC — equivalente ao "Celery beat" pedido pelo brief da Task 4, mas
usando a lib `schedule` + thread daemon (mesmo padrão de
app/workers/produtividade_scheduler.py e onedrive_sync_worker.py). Ver o
docstring de app/services/feedback_scheduler.py para o porquê de não usar
Celery neste projeto.

DESABILITADO por padrão: só é chamado a partir de app/main.py se
settings.feedback_deploy_enabled=True (env FEEDBACK_DEPLOY_ENABLED=true).
Mesma cautela que o próprio main.py já aplica a outros schedulers que tocam
produção (alerta/ESAJ/retenção/expiração ficam comentados como "DESABILITADO
até migração VPS") — este aqui pode fazer git push + docker restart reais
quando settings.feedback_deploy_dry_run=False, então fica opt-in explícito
em dois níveis independentes.
"""
import logging
import threading
import time
from datetime import datetime

import schedule

from app.config import settings
from app.services.feedback_scheduler import deploy_approved_feedback

logger = logging.getLogger(__name__)

_scheduler_state = {
    "running": False,
    "ultima_execucao": None,
    "ultima_execucao_status": None,
    "ultimo_resultado": None,
    "total_execucoes": 0,
    "total_erros": 0,
}


def obter_estado_scheduler() -> dict:
    return _scheduler_state.copy()


def _job_wrapper():
    logger.info("=" * 60)
    logger.info("Iniciando ciclo agendado de deploy de feedback (19h UTC)")
    logger.info("=" * 60)
    try:
        resultado = deploy_approved_feedback()
        _scheduler_state["ultima_execucao"] = datetime.utcnow().isoformat()
        _scheduler_state["ultima_execucao_status"] = "ok"
        _scheduler_state["ultimo_resultado"] = resultado
        _scheduler_state["total_execucoes"] += 1
        logger.info(f"✅ Ciclo de deploy de feedback concluído: {resultado}")
    except Exception as e:
        logger.error(f"❌ Falha no ciclo de deploy de feedback: {e}", exc_info=True)
        _scheduler_state["total_erros"] += 1
        _scheduler_state["ultima_execucao_status"] = "error"


def _run_scheduler_loop():
    hora = settings.feedback_deploy_hour  # "19:00" — o processo deve rodar em TZ=UTC (padrão dos containers deste projeto)
    logger.info(f"Scheduler de deploy de feedback iniciado (thread daemon) — diário às {hora} UTC")
    schedule.every().day.at(hora).do(_job_wrapper)

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Erro no scheduler loop de deploy de feedback: {e}", exc_info=True)
            time.sleep(60)


def iniciar_scheduler_feedback_deploy():
    if _scheduler_state["running"]:
        logger.warning("Scheduler de deploy de feedback já está em execução")
        return
    _scheduler_state["running"] = True
    thread = threading.Thread(target=_run_scheduler_loop, daemon=True, name="FeedbackDeploySync")
    thread.start()
    logger.info("✅ Scheduler de deploy de feedback iniciado")
