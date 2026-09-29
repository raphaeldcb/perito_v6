"""Router para endpoints de conciliação."""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Processo
from app.services import get_db
from . import service
from .schemas import CorrigirRequest, CorrigirResponse, ConciliarRequest, ConciliarResponse

router = APIRouter(prefix="/api/v1/conciliacao", tags=["conciliacao"])


@router.get("/corrigir", response_model=CorrigirResponse)
async def corrigir(
    valor: float,
    de: str,
    ate: str,
    indexador: str = "IPCA",
    user: User = Depends(get_current_user)
):
    """Teste da correção: quanto vale `valor` de `de` até `ate` pelo índice."""
    f = service.fator_correcao(indexador, de, ate)
    return CorrigirResponse(
        valor=valor,
        de=de,
        ate=ate,
        indexador=indexador,
        fator=round(f, 6),
        corrigido=round(valor * f, 2)
    )


@router.post("/conciliar", response_model=ConciliarResponse)
async def conciliar(
    body: ConciliarRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Casa um crédito (valor + data) com os processos. Se `candidatos` não vier,
    usa os processos que têm honorário. Body: {valor, data_credito, tolerancia?,
    indexador?, candidatos?:[{processo_id, numero_cnj, honorario, data_proposta}]}."""
    candidatos = body.candidatos
    if not candidatos:
        procs = db.query(Processo).filter(Processo.honorarios.isnot(None)).limit(800).all()
        candidatos = []
        for p in procs:
            if not p.honorarios:
                continue
            dp = p.created_at.date().isoformat() if p.created_at else None
            if dp:
                candidatos.append({
                    "processo_id": p.id,
                    "numero_cnj": p.numero_cnj,
                    "honorario": float(p.honorarios),
                    "data_proposta": dp
                })

    res = service.conciliar_credito(
        body.valor,
        body.data_credito,
        candidatos,
        float(body.tolerancia),
        body.indexador
    )

    return ConciliarResponse(
        total_candidatos=len(candidatos),
        matches=[r for r in res if r["casa"]][:10],
        top=res[:5]
    )
