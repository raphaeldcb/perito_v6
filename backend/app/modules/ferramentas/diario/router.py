"""
Diario (DJEN) Router — Diário Oficial Legal Journal Monitoring API Endpoints.

Endpoints:
- GET /api/v1/diario/config: Get current search configuration
- PUT /api/v1/diario/config: Save new search configuration
- POST /api/v1/diario/consultar: Execute one-off DJEN search
- POST /api/v1/diario/sincronizar: Run scheduled search with saved config
- POST /api/v1/diario/analisar-captacao: Score publications as opportunities (Qwen)
- GET /api/v1/diario/oportunidades: List scored opportunities
- PATCH /api/v1/diario/oportunidades/{id}/descartar: Mark opportunity as discarded
- POST /api/v1/diario/oportunidades/{id}/gerar-email: Draft email to lawyer (Qwen)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Job, Oportunidade
from app.services import get_db
from .schemas import ConfigInput, ConsultaInput, AnalisarInput
from .service import DiarioService

router = APIRouter(prefix="/api/v1/diario", tags=["diario"])


@router.get("/config")
async def get_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Retrieve current DJEN search configuration."""
    return DiarioService.get_config(db)


@router.put("/config")
async def salvar_config(payload: ConfigInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Save DJEN search configuration."""
    return DiarioService.save_config(db, payload.incluir, payload.excluir, payload.tribunais)


@router.post("/consultar")
async def consultar(payload: ConsultaInput, user: User = Depends(get_current_user)):
    """Execute one-off DJEN search (does not use saved config)."""
    return DiarioService.consultar(payload.tribunais, payload.incluir, payload.excluir, payload.dias)


@router.post("/sincronizar")
async def sincronizar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Run DJEN search using saved config and save new as opportunities."""
    return DiarioService.sincronizar(db)


@router.post("/analisar-captacao")
async def analisar_captacao(payload: AnalisarInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Send publications to Qwen for opportunity scoring (async job)."""
    job = Job(
        tipo="analisar_captacao",
        status="na_fila",
        payload={"publicacoes": payload.publicacoes[:12]}
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "mensagem": "Qwen avaliando as oportunidades (roda em segundo plano)."}


@router.get("/oportunidades")
async def listar_oportunidades(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List all opportunities scored by Qwen."""
    ops = db.query(Oportunidade).filter(Oportunidade.status != "descartado").order_by(
        Oportunidade.score.desc().nullslast()).limit(100).all()
    return [{
        "id": o.id,
        "tribunal": o.tribunal,
        "numero_processo": o.numero_processo,
        "area": o.area,
        "oportunidade": o.oportunidade,
        "defensoria": o.defensoria,
        "empresa_grande": o.empresa_grande,
        "oab_antiga": o.oab_antiga,
        "advogado_nome": o.advogado_nome,
        "advogado_oab": o.advogado_oab,
        "advogado_email": o.advogado_email,
        "merito_sem_pct": float(o.merito_sem_pct) if o.merito_sem_pct is not None else None,
        "merito_com_pct": float(o.merito_com_pct) if o.merito_com_pct is not None else None,
        "ressalvas": o.ressalvas,
        "resumo": o.resumo,
        "score": float(o.score) if o.score is not None else 0,
        "status": o.status,
        "email_rascunho": o.email_rascunho,
        "link": o.link,
    } for o in ops]


@router.patch("/oportunidades/{op_id}/descartar")
async def descartar_oportunidade(op_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Mark an opportunity as discarded."""
    o = db.query(Oportunidade).filter(Oportunidade.id == op_id).first()
    if o:
        o.status = "descartado"
        db.commit()
    return {"ok": True}


@router.post("/oportunidades/{op_id}/gerar-email")
async def gerar_email(op_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Draft email to lawyer for an opportunity (Qwen, async)."""
    o = db.query(Oportunidade).filter(Oportunidade.id == op_id).first()
    if not o:
        return {"erro": "não encontrada"}

    job = Job(
        tipo="rascunho_email_captacao",
        status="na_fila",
        payload={
            "oportunidade_id": o.id,
            "advogado_nome": o.advogado_nome,
            "numero_processo": o.numero_processo,
            "area": o.area,
            "merito_sem_pct": float(o.merito_sem_pct) if o.merito_sem_pct is not None else 50,
            "merito_com_pct": float(o.merito_com_pct) if o.merito_com_pct is not None else 70,
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id}


__all__ = ["router"]
