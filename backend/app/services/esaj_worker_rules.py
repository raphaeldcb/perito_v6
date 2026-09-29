"""
Regras de negócio para worker eSAJ — implementa limite 15x tentativas
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.job import Job

logger = logging.getLogger(__name__)


class ESAJWorkerRules:
    """Implementação de regras de negócio para protocolo eSAJ"""

    MAX_TENTATIVAS_ESAJ = 15

    @staticmethod
    def validar_antes_processar(db: Session, job_id: int) -> tuple[bool, str]:
        """
        Valida se job pode ser processado.
        Retorna (pode_processar, motivo)

        REGRA P0: Se tentativas_esaj >= 15 → BLOQUEAR
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False, f"Job {job_id} não encontrado"

        # Protocolo eSAJ só (outros tipos podem ter regra diferente)
        if "protocolo" not in job.tipo.lower() and "esaj" not in job.tipo.lower():
            return True, ""  # Não aplica regra

        # REGRA: Se já falhou 15 vezes
        if job.tentativas_esaj >= ESAJWorkerRules.MAX_TENTATIVAS_ESAJ:
            motivo = f"BLOQUEADO: eSAJ falhou {job.tentativas_esaj}x (máximo {ESAJWorkerRules.MAX_TENTATIVAS_ESAJ})"
            job.status = "falhou"
            job.bloqueado_pela_regra = "ESAJ_MAX_TENTATIVAS"
            job.erro = motivo
            db.commit()

            # Notificar Master
            logger.critical(f"🔴 PARADA: Job {job.id} ({job.tipo}) bloqueado após {job.tentativas_esaj} falhas. Notificar Master.")
            ESAJWorkerRules.notificar_master(db, job_id, motivo)

            return False, motivo

        return True, ""

    @staticmethod
    def incrementar_tentativa(db: Session, job_id: int, erro: str = ""):
        """Incrementa contador de tentativas e registra erro"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.tentativas_esaj += 1
        job.tentativas += 1

        if erro:
            job.erro = f"[Tentativa {job.tentativas_esaj}/{ESAJWorkerRules.MAX_TENTATIVAS_ESAJ}] {erro}"

        logger.warning(f"⚠️ eSAJ Tentativa {job.tentativas_esaj}/{ESAJWorkerRules.MAX_TENTATIVAS_ESAJ} — Job {job.id}")

        # Se atinge limite, bloquear
        if job.tentativas_esaj >= ESAJWorkerRules.MAX_TENTATIVAS_ESAJ:
            job.status = "falhou"
            job.bloqueado_pela_regra = "ESAJ_MAX_TENTATIVAS"
            logger.critical(f"🔴 PARADA: Job {job.id} bloqueado após {job.tentativas_esaj} falhas eSAJ")
            ESAJWorkerRules.notificar_master(db, job_id,
                f"Job {job.id} bloqueado: {ESAJWorkerRules.MAX_TENTATIVAS_ESAJ} tentativas falhadas")

        db.commit()

    @staticmethod
    def marcar_sucesso(db: Session, job_id: int, resultado: dict = None):
        """Marca job como sucesso e registra resultado"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "concluido"
        job.resultado = resultado or {}
        job.concluido_em = datetime.utcnow()
        job.bloqueado_pela_regra = None
        db.commit()

        logger.info(f"✅ eSAJ SUCESSO: Job {job.id} concluído em {job.tentativas_esaj} tentativa(s)")

    @staticmethod
    def notificar_master(db: Session, job_id: int, mensagem: str):
        """
        TODO: Implementar notificação real para Master.
        Por enquanto, apenas log crítico.

        Futura integração:
        - Enviar email para admin@ipcms.com.br
        - Criar notificação no dashboard
        - Alertar no Slack (se configurado)
        """
        logger.critical(f"🚨 NOTIFICAR MASTER (Job {job_id}): {mensagem}")
        # TODO: implementar notificação real
