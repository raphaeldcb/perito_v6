"""Rotas administrativas do Perito System.

Endpoints para gerenciar sistema, sincronizações, e monitoramento.
Requer autenticação e permissão de admin.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.job import Job
from app.models.processo import Processo
from app.services.database import get_db
from app.middleware.auth import get_current_user
from app.workers.onedrive_sync_worker import (
    obter_estado_scheduler,
    executar_sync_agora,
    iniciar_scheduler_onedrive,
)
from app.utils import circuit_breaker_status

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Valida se usuário é admin."""
    if not user or not user.role or user.role.name not in ["admin", "coordenador"]:
        raise HTTPException(status_code=403, detail="Acesso negado: requer role admin")
    return user


@router.get("/onedrive-sync-status")
async def obter_status_onedrive_sync(admin: User = Depends(require_admin)):
    """
    GET /api/v1/admin/onedrive-sync-status

    Retorna status atual do sync OneDrive:
    - Última sincronização
    - Próxima sincronização programada
    - Contadores (criados, atualizados, erros)
    - Estado do scheduler
    """
    estado = obter_estado_scheduler()

    return {
        "scheduler_running": estado.get("running", False),
        "ultima_sync": estado.get("ultima_sync"),
        "proxima_sync": estado.get("proxima_sync"),
        "ultima_sync_status": estado.get("ultima_sync_status"),
        "total_execucoes": estado.get("total_execucoes", 0),
        "total_erros": estado.get("total_erros", 0),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/onedrive-sync/executar-agora")
async def forcar_sync_onedrive(
    admin: User = Depends(require_admin),
) -> dict:
    """
    POST /api/v1/admin/onedrive-sync/executar-agora

    Força uma sincronização imediata do OneDrive (sob demanda).
    Pode levar alguns segundos a minutos dependendo do tamanho da pasta.

    Resposta:
    {
        "status": "started" | "disabled",
        "message": "Sync iniciado...",
        "scheduler_state": {...}
    }
    """
    try:
        estado_anterior = obter_estado_scheduler()
        executar_sync_agora()
        estado_novo = obter_estado_scheduler()

        return {
            "status": "started",
            "message": "Sincronização iniciada (verifique o status em segundos)",
            "scheduler_state": estado_novo,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar sync: {str(e)}",
        )


@router.get("/health")
async def health_check(admin: User = Depends(require_admin)):
    """
    GET /api/v1/admin/health

    Health check administrativo.
    """
    estado = obter_estado_scheduler()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler_status": estado.get("ultima_sync_status", "unknown"),
        "service": "perito-v6",
    }


@router.post("/reset-jobs-orfaos")
async def reset_jobs_orfaos(
    admin: User = Depends(require_admin),
    timeout_minutos: int = Query(5, description="Minutos sem heartbeat para considerar órfão"),
    db: Session = Depends(get_db),
) -> dict:
    """
    POST /api/v1/admin/reset-jobs-orfaos

    Encontra jobs com status='processando' + last_heartbeat > timeout_minutos.
    Reseta para 'na_fila' com tentativa++.

    Query params:
    - timeout_minutos: Minutos sem heartbeat para considerar órfão (default: 5)

    Retorna:
    {
        "resgatados": N,
        "jobs": [
            {"id": 1, "tipo": "protocolo", "tentativa_anterior": 1, "tentativa_nova": 2},
            ...
        ],
        "timestamp": "2026-07-16T15:00:00"
    }
    """
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutos)

        # Encontra jobs órfãos: processando + heartbeat expirado (ou nunca teve heartbeat)
        jobs_orfaos = db.query(Job).filter(
            Job.status == "processando",
            (Job.last_heartbeat.is_(None) | (Job.last_heartbeat < cutoff))
        ).all()

        resgatados = []
        for job in jobs_orfaos:
            tentativa_anterior = job.tentativas
            job.status = "na_fila"
            job.tentativas += 1
            job.executor = None  # Libera executor
            job.last_heartbeat = None  # Reseta heartbeat
            db.add(job)

            resgatados.append({
                "id": job.id,
                "tipo": job.tipo,
                "tentativa_anterior": tentativa_anterior,
                "tentativa_nova": job.tentativas,
            })

        db.commit()

        return {
            "resgatados": len(resgatados),
            "jobs": resgatados,
            "timeout_minutos": timeout_minutos,
            "cutoff": cutoff.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao resetar jobs órfãos: {str(e)}",
        )


@router.get("/circuit-breakers")
async def obter_status_circuit_breakers(admin: User = Depends(require_admin)):
    """
    GET /api/v1/admin/circuit-breakers

    Retorna status de todos os circuit breakers (resiliência de APIs externas).

    Estados:
    - CLOSED: funcionando normalmente
    - OPEN: serviço indisponível (fail-fast)
    - HALF_OPEN: testando recuperação

    Response:
    {
      "qwen": {"state": "CLOSED", "failure_count": 0, "threshold": 5, ...},
      "inter": {"state": "OPEN", "failure_count": 5, "threshold": 5, ...},
      "djen": {...},
      "graph_api": {...},
      "bcb": {...},
      "timestamp": "2026-07-16T12:34:56.789Z"
    }
    """
    breakers = circuit_breaker_status()
    return {
        "breakers": breakers,
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(breakers),
        "abertos": sum(1 for b in breakers.values() if b.get("state") == "OPEN"),
    }


@router.post("/populate-dna")
async def populate_dna_from_partes(
    db: Session = Depends(get_db),
) -> dict:
    """Popula participantes_dna a partir de partes."""
    processos = db.query(Processo).all()
    count = 0

    for p in processos:
        if not p.partes or not isinstance(p.partes, list):
            continue

        if p.participantes_dna and p.participantes_dna != []:
            continue

        dna = []
        for parte in p.partes:
            if isinstance(parte, dict):
                dna.append({
                    "tipo": parte.get("papel", "desconhecido"),
                    "nome_real": parte.get("nome", ""),
                    "nome_doc": parte.get("nome", "")
                })

        if dna:
            p.participantes_dna = dna
            count += 1

    db.commit()
    return {
        "status": "sucesso",
        "processos_atualizados": count,
        "timestamp": datetime.utcnow().isoformat(),
    }
