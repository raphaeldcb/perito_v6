from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models import Job, Intimacao
from app.services import get_db
from app.middleware import get_current_user
from app.config import settings
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/pje", tags=["pje"])


def verificar_agente(x_agent_key: str = Header(None)):
    if not settings.agent_api_key:
        raise HTTPException(status_code=503, detail="AGENT_API_KEY não configurada")
    if x_agent_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Chave de agente inválida")


class BaixarAutosInput(BaseModel):
    numero_cnj: str
    tribunal: str = "TJMT"


@router.post("/baixar-autos")
async def enfileirar_download_autos(
    payload: BaixarAutosInput,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    job = Job(
        tipo="pje_download_autos",
        payload={
            "numero_cnj": payload.numero_cnj,
            "tribunal": payload.tribunal
        },
        status="na_fila",
        executor="mac-agent-pje"
    )
    db.add(job)
    db.commit()
    
    return {
        "job_id": job.id,
        "numero_cnj": payload.numero_cnj,
        "status": "na_fila"
    }


@router.get("/fila")
async def listar_fila(
    skip: int = 0,
    limit: int = 10,
    status_filtro: str = "na_fila",
    db: Session = Depends(get_db),
    agent=Depends(verificar_agente)
):
    query = db.query(Job).filter(
        Job.tipo == "pje_download_autos",
        Job.status == status_filtro
    )
    
    total = query.count()
    jobs = query.order_by(Job.id.asc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [
            {
                "id": j.id,
                "payload": j.payload,
                "criado_em": j.created_at.isoformat()
            }
            for j in jobs
        ]
    }


@router.patch("/{job_id}/concluir")
async def concluir_download(
    job_id: int,
    resultado: dict,
    db: Session = Depends(get_db),
    agent=Depends(verificar_agente)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404)

    if resultado.get("sucesso"):
        job.status = "concluido"
        job.resultado = resultado

        intimacao_id = job.payload.get("intimacao_id")
        if intimacao_id:
            intimacao = db.query(Intimacao).filter(Intimacao.id == intimacao_id).first()
            if intimacao:
                intimacao.pdf_path = resultado.get("pdf_path")
                intimacao.status = "autos_baixados"
    else:
        job.status = "erro"
        job.erro = resultado.get("erro")

    db.commit()
    return {"ok": True}


# ====== FERRAMENTA DASHBOARD ======


class BaixarAutosFerramentaRequest(BaseModel):
    intimacao_id: int


@router.post("/ferramenta/baixar-autos")
async def ferramenta_baixar_autos_pje(
    req: BaixarAutosFerramentaRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Ferramenta do dashboard: clica botão e enfileira automaticamente.

    Windows agent detecta via GET /api/v1/pje/fila
    → abre Chrome + A3 + baixa autos automaticamente

    Usuário só coloca A3 + Authenticator quando solicitado.
    """

    intimacao = db.query(Intimacao).filter(Intimacao.id == req.intimacao_id).first()
    if not intimacao:
        raise HTTPException(status_code=404, detail="Intimação não encontrada")

    if intimacao.processo.tribunal != "TJMT":
        raise HTTPException(status_code=400, detail="Ferramenta só para TJMT")

    if intimacao.pdf_path:
        return {
            "ok": True,
            "job_id": None,
            "numero_cnj": intimacao.processo.numero_cnj,
            "status": "✅ Autos já baixados",
            "pdf_path": intimacao.pdf_path
        }

    job_existente = db.query(Job).filter(
        Job.tipo == "pje_download_autos",
        Job.payload["intimacao_id"].astext == str(intimacao.id),
        Job.status.in_(["na_fila", "processando"])
    ).first()

    if job_existente:
        return {
            "ok": True,
            "job_id": job_existente.id,
            "numero_cnj": intimacao.processo.numero_cnj,
            "status": f"⏳ Já na fila (Job #{job_existente.id})"
        }

    job = Job(
        tipo="pje_download_autos",
        payload={
            "numero_cnj": intimacao.processo.numero_cnj,
            "tribunal": "TJMT",
            "intimacao_id": intimacao.id
        },
        status="na_fila",
        executor="windows-agent-pje"
    )
    db.add(job)
    db.commit()

    return {
        "ok": True,
        "job_id": job.id,
        "numero_cnj": intimacao.processo.numero_cnj,
        "status": "🚀 Enfileirado — abrindo Chrome no Windows...",
        "instrucao": "Coloque A3 + Authenticator quando solicitado"
    }


@router.get("/ferramenta/status/{job_id}")
async def ferramenta_status_download(
    job_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Poll em tempo real do status do download."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404)

    status_map = {
        "na_fila": "⏳ Aguardando Windows...",
        "processando": "🔄 Baixando autos (Chrome aberto)...",
        "concluido": f"✅ Pronto! {job.resultado.get('tamanho_bytes', 0)} bytes",
        "erro": f"❌ Erro: {job.erro}"
    }

    return {
        "job_id": job_id,
        "status": status_map.get(job.status, job.status),
        "resultado": job.resultado if job.status == "concluido" else None
    }
