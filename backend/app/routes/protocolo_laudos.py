import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Laudo
from app.services import get_db, monitor_pastas_protocolo, monitor_caixa_postal_esaj
from app.decorators.require_feature import require_feature_flag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/protocolo", tags=["protocolo"])


@router.post("/monitor-pastas")
async def disparar_monitor_pastas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """POST /api/v1/protocolo/monitor-pastas - dispara monitor D:\Laudos\ e D:\Oficios\"""
    try:
        # Pode rodar em background ou síncrono (depende de UX)
        resultado = monitor_pastas_protocolo.monitorar_pastas(db)

        logger.info(f"Monitor pastas disparado por {current_user.email}: {resultado}")
        return {
            "status": "monitor_disparado",
            "resultado": resultado,
            "mensagem": f"Encontrados {resultado['laudos_encontrados']} laudos, {resultado['oficios_encontrados']} ofícios. Jobs enfileirados: {resultado['jobs_enfileirados']}"
        }

    except Exception as e:
        logger.error(f"Erro ao disparar monitor: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao disparar monitor: {e}")


@router.post("/{laudo_id}/protocolar")
async def protocolar_laudo_manual(
    laudo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """POST /api/v1/protocolo/{laudo_id}/protocolar - protocola laudo especifico (manual)"""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")

    if laudo.status != "emitido":
        raise HTTPException(
            status_code=400,
            detail=f"Laudo deve estar emitido (status='emitido'), atual: {laudo.status}"
        )

    try:
        # TODO: Integrar com protocolo_automatico.py existente
        # Por enquanto, apenas log
        logger.info(f"Protocolo manual disparado para laudo {laudo_id} por {current_user.email}")

        return {
            "status": "protocolo_enfileirado",
            "laudo_id": laudo_id,
            "mensagem": "Protocolo aguardando execução (A3 fallback — autorize manualmente)"
        }

    except Exception as e:
        logger.error(f"Erro ao protocolar laudo {laudo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")


@router.get("/status/{numero_protocolo}")
async def consultar_status_protocolo(
    numero_protocolo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """GET /api/v1/protocolo/status/{numero_protocolo} - consulta caixa postal ESAJ"""
    try:
        # TODO: Integrar com monitor_caixa_postal_esaj.consultar_status_protocolo
        resultado = monitor_caixa_postal_esaj.consultar_status_protocolo(numero_protocolo)

        logger.info(f"Consulta status {numero_protocolo} por {current_user.email}")
        return resultado

    except Exception as e:
        logger.error(f"Erro ao consultar status {numero_protocolo}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")


@router.post("/monitorar-caixa-postal")
async def disparar_monitor_caixa_postal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """POST /api/v1/protocolo/monitorar-caixa-postal - dispara polling ESAJ a cada 30 minutos"""
    try:
        resultado = monitor_caixa_postal_esaj.monitorar_caixa_postal_esaj(db)

        logger.info(f"Monitor ESAJ disparado por {current_user.email}: {resultado}")
        return {
            "status": "monitor_esaj_disparado",
            "resultado": resultado,
            "mensagem": f"Recibos encontrados: {resultado['recibos_encontrados']}, laudos atualizados: {resultado['laudos_atualizados']}"
        }

    except Exception as e:
        logger.error(f"Erro ao disparar monitor ESAJ: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {e}")
