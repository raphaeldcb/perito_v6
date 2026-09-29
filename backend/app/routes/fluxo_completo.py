"""
Fluxo automático completo: Intimação → Ofício → Protocola → Laudo → Protocola
Dispara toda a cadeia de jobs com um único endpoint.

O laudo é gerado pelo mac_agent (Ollama/Qwen local — mesma infra da análise de
intimações); o backend materializa (LaudoVersao + DOCX) quando o job conclui.
Os protocolos (A3) também vão para a fila do mac_agent.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Intimacao, Oficio, Job, Laudo
from app.services import get_db
from app.services.oficio_generator import gerar_oficio
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/fluxo", tags=["fluxo"])
logger = logging.getLogger(__name__)


@router.post("/completo/{intimacao_id}")
async def disparar_fluxo_completo(
    intimacao_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Dispara fluxo completo automático:
    1. Gera OFÍCIO
    2. Enfileira protocolo OFÍCIO (A3)
    3. Enfileira geração do LAUDO (Qwen no mac_agent)
    4. Enfileira protocolo LAUDO (A3, aguarda o laudo)

    Retorna IDs dos jobs para monitoramento.
    """
    intimacao = db.query(Intimacao).filter(Intimacao.id == intimacao_id).first()
    if not intimacao:
        raise HTTPException(status_code=404, detail="Intimação não encontrada")

    if not intimacao.dados_estruturados:
        raise HTTPException(status_code=400, detail="Intimação sem análise Qwen — processe primeiro")

    if not intimacao.processo_id:
        raise HTTPException(status_code=400, detail="Intimação sem processo vinculado")

    job_ids = {"oficio": None, "laudo": None}

    try:
        # 1. Gera Ofício
        resultado_oficio = gerar_oficio(intimacao, tipo="requerimento")

        # Salva Oficio no BD
        oficio = Oficio(
            intimacao_id=intimacao_id,
            processo_id=intimacao.processo_id,
            tipo="requerimento",
            arquivo_docx_path=resultado_oficio["oficio_docx_path"],
            status="gerado",
        )
        db.add(oficio)
        db.flush()

        # 2. Enfileira protocolo OFÍCIO
        job_oficio = Job(
            tipo="protocolo_oficio",
            payload={
                "intimacao_id": intimacao_id,
                "oficio_id": oficio.id,
                "numero_cnj": intimacao.processo.numero_cnj if intimacao.processo else None,
                "arquivo_path": resultado_oficio["oficio_docx_path"],
            },
            status="na_fila",
        )
        db.add(job_oficio)
        db.flush()
        job_ids["oficio"] = job_oficio.id
        oficio.status = "protocolo_enfileirado"

        # 3. Cria o Laudo e enfileira a geração (mac_agent + Ollama local)
        dados = intimacao.dados_estruturados or {}
        quesitos = dados.get("quesitos") or []
        processo = intimacao.processo
        laudo = Laudo(
            processo_id=intimacao.processo_id,
            tipo_laudo="contabil",  # TODO: detectar do tipo_pericia
            perito_id=user.id,
            empresa_id=getattr(user, "empresa_id", None) or 1,
            quesitos=json.dumps(quesitos, ensure_ascii=False),
            status="rascunho",
        )
        db.add(laudo)
        db.flush()

        job_laudo = Job(
            tipo="gerar_laudo",
            payload={
                "intimacao_id": intimacao_id,
                "processo_id": intimacao.processo_id,
                "laudo_id": laudo.id,
                "tipo_laudo": laudo.tipo_laudo,
                # contexto para o prompt do laudo (mac_agent não acessa o BD)
                "numero_cnj": getattr(processo, "numero_cnj", None),
                "tribunal": getattr(processo, "tribunal", None) or dados.get("vara"),
                "autor": getattr(processo, "autor", None),
                "reu": getattr(processo, "reu", None),
                "quesitos": quesitos,
                "resumo": dados.get("resumo"),
            },
            status="na_fila",
        )
        db.add(job_laudo)
        db.flush()
        job_ids["laudo"] = job_laudo.id

        # 4. Enfileira protocolo LAUDO (só é liberado quando o laudo concluir)
        job_protocolo_laudo = Job(
            tipo="protocolo_laudo",
            payload={
                "intimacao_id": intimacao_id,
                "processo_id": intimacao.processo_id,
                "laudo_id": laudo.id,
                "numero_cnj": intimacao.processo.numero_cnj if intimacao.processo else None,
                "aguardar_job_id": job_laudo.id,  # Espera laudo pronto
            },
            status="na_fila",
        )
        db.add(job_protocolo_laudo)
        db.flush()

        db.commit()

        logger.info(f"🚀 Fluxo completo disparado para intimação {intimacao_id} — Jobs: {job_ids}")

        return {
            "status": "disparado",
            "intimacao_id": intimacao_id,
            "job_oficio_id": job_ids["oficio"],
            "job_laudo_id": job_ids["laudo"],
            "mensagem": "Fluxo enfileirado. Acompanhe via GET /api/v1/fluxo/status/{intimacao_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao disparar fluxo: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.get("/status/{intimacao_id}")
async def status_fluxo(
    intimacao_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retorna status completo do fluxo para uma intimação."""
    intimacao = db.query(Intimacao).filter(Intimacao.id == intimacao_id).first()
    if not intimacao:
        raise HTTPException(status_code=404, detail="Intimação não encontrada")

    oficio = (
        db.query(Oficio)
        .filter(Oficio.intimacao_id == intimacao_id)
        .order_by(Oficio.id.desc())
        .first()
    )

    # jobs do fluxo desta intimação (payload carrega intimacao_id)
    jobs = (
        db.query(Job)
        .filter(Job.tipo.in_(["gerar_laudo", "protocolo_laudo", "protocolo_oficio"]))
        .order_by(Job.id.desc())
        .limit(300)
        .all()
    )

    def _job_de(tipo):
        return next(
            (j for j in jobs if j.tipo == tipo and (j.payload or {}).get("intimacao_id") == intimacao_id),
            None,
        )

    job_laudo = _job_de("gerar_laudo")
    job_protocolo_laudo = _job_de("protocolo_laudo")

    protocolo_laudo_numero = None
    if job_protocolo_laudo and job_protocolo_laudo.resultado:
        protocolo_laudo_numero = job_protocolo_laudo.resultado.get("protocolo_numero")

    return {
        "intimacao_id": intimacao_id,
        "status_intimacao": intimacao.status,
        "oficio": {
            "id": oficio.id,
            "status": oficio.status,
            "numero_protocolo": oficio.numero_protocolo,
        } if oficio else None,
        "laudo": {
            "id": (job_laudo.payload or {}).get("laudo_id") if job_laudo else None,
            "status": job_laudo.status if job_laudo else "nao_gerado",
            "erro": job_laudo.erro if job_laudo else None,
            "numero_protocolo": protocolo_laudo_numero,
            "protocolo_status": job_protocolo_laudo.status if job_protocolo_laudo else None,
        },
    }
