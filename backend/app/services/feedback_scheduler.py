"""Deploy automático de feedback aprovado — Task 4 do plano de Feedback &
Error Reporting System (docs/superpowers/plans/2026-08-04-feedback-system.md).

Roda 1x/dia às 19h UTC: busca FeedbackReport com status=APPROVED e ainda não
implementado, valida que o ambiente está saudável (pre-flight), e tenta
aplicar o fix via /free (ccr code) + git push + docker restart. Sucesso ->
IMPLEMENTED; qualquer falha (pre-flight ou deploy) -> DEPLOY_FAILED, para
revisão manual.

⚠️ DESVIOS DO TEXTO ORIGINAL DO BRIEF (task-4-brief.md) — e por quê:

  1. **Sem Celery de verdade.** Este projeto não tem Celery em lugar
     nenhum: não está em requirements_v6.txt, não há broker Redis/RabbitMQ
     no docker-compose.yml, não existe app/celery_app.py. TODO agendamento
     hoje usa a lib `schedule` (já em requirements_v6.txt) + thread daemon
     — ver app/workers/produtividade_scheduler.py e onedrive_sync_worker.py,
     mesmo padrão replicado em app/workers/feedback_deploy_scheduler.py.
     Introduzir um broker novo só para esta task diária seria
     infraestrutura desproporcional ao problema (mesmo raciocínio já
     documentado no docstring do produtividade_scheduler.py). `@shared_task`
     é aplicado como decorator *opcional*: se `celery` estiver instalado
     no ambiente, `deploy_approved_feedback` vira uma task Celery de verdade
     (nome exato "deploy_approved_feedback", como pedido); se não estiver
     (o caso hoje), é só uma função Python normal — testável e chamável
     direto, sem broker.
  2. **`pg_isready` trocado por `SELECT 1` via SessionLocal.** O brief pede
     `pg_isready -h localhost`, que assume Postgres + cliente CLI
     instalado. Em dev local (e no .env do repo) `DATABASE_URL` é sqlite
     (`sqlite:///./v6.db`) — `pg_isready` falharia sempre em dev, mesmo
     com o banco saudável. Uma query real via SessionLocal funciona nos
     dois dialetos e é o mesmo padrão que
     app/services/health_check.py:check_db() já usa.
  3. **Dois interruptores antes de qualquer ação real**, seguindo o
     precedente já existente em app/main.py de deixar schedulers que tocam
     produção DESABILITADOS por padrão (alerta/ESAJ/retenção/expiração
     comentados com "DESABILITADO até migração VPS"):
       - `settings.feedback_deploy_enabled` (default False) — controla se
         a THREAD do scheduler sequer é iniciada no startup do backend.
       - `dry_run` (default `settings.feedback_deploy_dry_run`, default
         True) — controla se `_deploy_with_free` executa git/docker de
         verdade ou só loga o que faria. Isso é o que permite testar o
         fluxo inteiro (pre-flight + transição de status) sem nunca tocar
         em git/docker reais.
  4. **Caminhos/remote/container vêm de `settings`**, não hardcoded —
     `VPS_BACKEND_PATH`, `VPS_GIT_REMOTE`, `VPS_GIT_BRANCH`,
     `DOCKER_BACKEND_CONTAINER`, `BACKEND_HEALTH_URL` em app/config/settings.py.
"""
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Optional

import requests
from sqlalchemy import text

from app.config import settings
from app.services.database import SessionLocal
from app.models.feedback import FeedbackReport

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:  # celery não é dependência deste projeto — ver docstring acima
    def shared_task(*_dargs, **_dkwargs):
        def _decorator(fn):
            return fn
        return _decorator


@shared_task(name="deploy_approved_feedback")
def deploy_approved_feedback(dry_run: Optional[bool] = None) -> dict:
    """Executar diariamente às 19h UTC: deploy de feedback aprovado com pre-flight checks.

    Args:
        dry_run: se None, usa settings.feedback_deploy_dry_run (default
            True). Passe False explicitamente só depois de validar
            pre-flight + fluxo em ambiente controlado.

    Returns:
        {"deployed": int, "failed": int}
    """
    effective_dry_run = settings.feedback_deploy_dry_run if dry_run is None else dry_run
    logger.info(f"=== Iniciando ciclo de deploy de feedback (dry_run={effective_dry_run}) ===")

    db = SessionLocal()
    try:
        reports = (
            db.query(FeedbackReport)
            .filter(
                FeedbackReport.status == "APPROVED",
                FeedbackReport.implemented_at.is_(None),
            )
            .all()
        )

        if not reports:
            logger.info("Nenhum feedback aprovado para deploy")
            return {"deployed": 0, "failed": 0}

        deployed = 0
        failed = 0

        for report in reports:
            try:
                if not _pre_flight_checks():
                    logger.warning(f"Pre-flight checks falharam para report {report.id} — pulando (mantém APPROVED)")
                    failed += 1
                    continue

                success = _deploy_with_free(report, dry_run=effective_dry_run)

                if success:
                    report.status = "IMPLEMENTED"
                    report.implemented_at = datetime.utcnow()
                    db.add(report)
                    deployed += 1
                    logger.info(f"✅ Deployed feedback {report.id} (dry_run={effective_dry_run})")
                else:
                    report.status = "DEPLOY_FAILED"
                    db.add(report)
                    failed += 1
                    logger.error(f"❌ Deploy failed for feedback {report.id}")

            except Exception as e:
                logger.error(f"Erro ao processar feedback {report.id}: {e}", exc_info=True)
                report.status = "DEPLOY_FAILED"
                db.add(report)
                failed += 1

        db.commit()
        logger.info(f"Ciclo de deploy concluído: {deployed} sucesso, {failed} falha(s)")
        return {"deployed": deployed, "failed": failed}

    finally:
        db.close()


def _pre_flight_checks() -> bool:
    """Valida que o ambiente está saudável antes de qualquer deploy.

    Três checks independentes, cada um logado (INFO se OK, ERROR se falhar):
      1. Docker respondendo (`docker ps -q`).
      2. Backend respondendo (`GET settings.backend_health_url`).
      3. Banco de dados acessível (`SELECT 1` via SessionLocal).
    """
    docker_ok = _check_docker()
    backend_ok = _check_backend_health()
    database_ok = _check_database()

    all_ok = docker_ok and backend_ok and database_ok
    if all_ok:
        logger.info("✅ Pre-flight checks passed (docker + backend + database)")
    else:
        logger.error(
            "❌ Pre-flight checks FAILED "
            f"(docker={docker_ok}, backend={backend_ok}, database={database_ok})"
        )
    return all_ok


def _check_docker() -> bool:
    if not shutil.which("docker"):
        logger.error("Pre-flight FAIL: binário `docker` não encontrado no PATH")
        return False
    try:
        result = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error(f"Pre-flight FAIL: docker não respondeu (rc={result.returncode}): {result.stderr.strip()}")
            return False
        logger.info("Pre-flight OK: Docker rodando")
        return True
    except Exception as e:
        logger.error(f"Pre-flight FAIL: erro ao checar docker: {e}")
        return False


def _check_backend_health() -> bool:
    try:
        resp = requests.get(settings.backend_health_url, timeout=5)
        if resp.status_code == 200:
            logger.info("Pre-flight OK: Backend UP")
            return True
        logger.error(f"Pre-flight FAIL: backend health retornou HTTP {resp.status_code}")
        return False
    except Exception as e:
        logger.error(f"Pre-flight FAIL: backend health inacessível ({settings.backend_health_url}): {e}")
        return False


def _check_database() -> bool:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.info("Pre-flight OK: Database UP")
        return True
    except Exception as e:
        logger.error(f"Pre-flight FAIL: database inacessível: {e}")
        return False
    finally:
        db.close()


def _deploy_with_free(report: FeedbackReport, dry_run: bool = True) -> bool:
    """Deploy usando /free (ccr code, Qwen local — zero Opus).

    Em dry_run=True (padrão), loga cada comando que SERIA executado e
    retorna True sem tocar em git/docker de verdade.
    """
    prompt = (
        f"Feedback a implementar:\n"
        f"Título: {report.title}\n"
        f"Descrição: {report.description}\n"
        f"Severity: {report.severity}\n\n"
        f"Gerar um fix mínimo para este feedback. "
        f"Retornar apenas o código a ser adicionado/modificado em JSON."
    )
    cmd = ["ccr", "code", "--model", "qwen:14b", "--prompt", prompt]
    commit_msg = f"fix: {report.title} (feedback #{report.id})"

    if dry_run:
        logger.info(f"[DRY-RUN] executaria: ccr code --model qwen:14b --prompt <{len(prompt)} chars>")
        logger.info(f"[DRY-RUN] git -C {settings.vps_backend_path} add -A")
        logger.info(f"[DRY-RUN] git -C {settings.vps_backend_path} commit -m {commit_msg!r}")
        logger.info(f"[DRY-RUN] git -C {settings.vps_backend_path} push {settings.vps_git_remote} {settings.vps_git_branch}")
        logger.info(f"[DRY-RUN] docker restart {settings.docker_backend_container}")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"Deploy falhou (ccr code, rc={result.returncode}): {result.stderr.strip()}")
            return False

        subprocess.run(["git", "add", "-A"], cwd=settings.vps_backend_path, capture_output=True, timeout=30)

        commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=settings.vps_backend_path, capture_output=True, text=True, timeout=30,
        )
        logger.info(f"git commit: {(commit.stdout or commit.stderr).strip()}")

        push = subprocess.run(
            ["git", "push", settings.vps_git_remote, settings.vps_git_branch],
            cwd=settings.vps_backend_path, capture_output=True, text=True, timeout=60,
        )
        if push.returncode != 0:
            logger.error(f"git push falhou: {push.stderr.strip()}")
            return False

        restart = subprocess.run(
            ["docker", "restart", settings.docker_backend_container],
            capture_output=True, text=True, timeout=60,
        )
        if restart.returncode != 0:
            logger.error(f"docker restart falhou: {restart.stderr.strip()}")
            return False

        return True

    except subprocess.TimeoutExpired as e:
        logger.error(f"Deploy timeout: {e}")
        return False
    except Exception as e:
        logger.error(f"Deploy exception: {e}", exc_info=True)
        return False
