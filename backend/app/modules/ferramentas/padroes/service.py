"""Business logic for padroes de cálculo (pattern calculation)."""

import logging
from app.jobs.interpretar_decisao_oficial import executar_interpretar_decisao
from app.models import Job
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)


def executar_padrao_em_background(job_id: int, padrao_id: int, processo_id: int) -> None:
    """Abre sua própria sessão — a do request já fechou quando o
    BackgroundTask roda (mesmo padrão de app/workers/produtividade_scheduler.py).

    Args:
        job_id: ID do job para atualizar status
        padrao_id: ID do padrão de cálculo
        processo_id: ID do processo
    """
    db = SessionLocal()
    try:
        executar_interpretar_decisao(job_id, padrao_id, processo_id, db)
    except Exception as e:
        logger.exception(f"[aplicar-padrao] job {job_id} falhou de forma inesperada")
        job = db.query(Job).filter(Job.id == job_id).first()
        if job and job.status not in ("concluido", "erro"):
            job.status = "erro"
            job.erro = str(e)[:2000]
            db.commit()
    finally:
        db.close()
