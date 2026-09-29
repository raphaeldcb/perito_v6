"""Rotas do Motor de Propostas — API completa para geração, revisão e aprovação."""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.middleware import get_current_user
from app.models import User, Processo, Intimacao, KanbanCartao, KanbanColuna, KanbanHistorico
from app.models.proposta import PropostaMotor, PropostaStatus, PropostaFeedback
from app.services import get_db
from app.services.proposta_motor import PropostaOrchestrator, BuscadorSimilares
from app.decorators.require_feature import require_feature_flag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/propostas", tags=["propostas"])


@router.post("/gerar")
async def gerar_proposta(
    file: UploadFile = File(...),
    processo_id: Optional[int] = None,
    intimacao_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload de PDF intimação → Pipeline completo de proposta.

    Retorna: {proposta_id, status, valor_recomendado, motivo, arquivo_docx}
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Arquivo deve ser PDF")

    try:
        # Salva PDF temporário
        pdf_dir = "/tmp/propostas_input"
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")

        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Se não temos processo_id, tenta buscar da intimação
        if not processo_id and intimacao_id:
            intim = db.query(Intimacao).get(intimacao_id)
            if intim:
                processo_id = intim.processo_id

        if not processo_id:
            raise HTTPException(400, "processo_id ou intimacao_id é obrigatório")

        # Valida processo existe
        proc = db.query(Processo).get(processo_id)
        if not proc:
            raise HTTPException(404, "Processo não encontrado")

        # Pipeline assincronamente (em produção, fila de jobs)
        proposta = await PropostaOrchestrator.processar_pdf(
            db=db,
            pdf_path=pdf_path,
            intimacao_id=intimacao_id,
            processo_id=processo_id,
            usuario_id=user.id,
        )

        return {
            "ok": True,
            "proposta_id": proposta.id,
            "status": proposta.status.value if proposta.status else "draft",
            "valor_recomendado": float(proposta.valor_recomendado or 0),
            "valor_alternativa": float(proposta.valor_alternativa or 0),
            "motivo": proposta.motivo_recomendacao,
            "area": proposta.area_nome,
            "arquivo_docx": proposta.arquivo_docx_path,
            "analista_id": proposta.analista_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar proposta: {e}")
        raise HTTPException(500, f"Erro: {str(e)}")


@router.get("/{proposta_id}")
async def obter_proposta(
    proposta_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Obtém detalhes completos da proposta."""
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta:
        raise HTTPException(404, "Proposta não encontrada")

    return {
        "id": proposta.id,
        "processo_id": proposta.processo_id,
        "status": proposta.status.value if proposta.status else None,
        "juiz": proposta.juiz,
        "comarca": proposta.comarca,
        "area": proposta.area_nome,
        "fls": proposta.fls,
        "valor_causa": float(proposta.valor_causa or 0),
        "valor_recomendado": float(proposta.valor_recomendado or 0),
        "valor_alternativa": float(proposta.valor_alternativa or 0),
        "motivo": proposta.motivo_recomendacao,
        "analise_juiz": proposta.analise_juiz,
        "analise_complexidade": proposta.analise_complexidade,
        "propostas_similares": proposta.propostas_similares,
        "arquivo_docx": proposta.arquivo_docx_path,
        "analista_id": proposta.analista_id,
        "data_vencimento": proposta.data_vencimento.isoformat() if proposta.data_vencimento else None,
        "data_criacao": proposta.created_at.isoformat() if proposta.created_at else None,
    }


@router.get("")
async def listar_propostas(
    status: Optional[str] = None,
    area_id: Optional[int] = None,
    vencidas_apenas: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lista propostas com filtros.
    ?status=draft&area_id=30&vencidas_apenas=true
    """
    query = db.query(PropostaMotor)

    if status:
        query = query.filter(PropostaMotor.status == status)

    if area_id:
        query = query.filter(PropostaMotor.area_id == area_id)

    if vencidas_apenas:
        hoje = datetime.utcnow()
        query = query.filter(PropostaMotor.data_vencimento <= hoje)

    propostas = query.order_by(desc(PropostaMotor.created_at)).limit(100).all()

    return [
        {
            "id": p.id,
            "processo": p.processo.numero_cnj if p.processo else None,
            "juiz": p.juiz,
            "status": p.status.value if p.status else None,
            "area": p.area_nome,
            "valor_recomendado": float(p.valor_recomendado or 0),
            "data_vencimento": p.data_vencimento.isoformat() if p.data_vencimento else None,
            "dias_restantes": (p.data_vencimento - datetime.utcnow()).days if p.data_vencimento else None,
            "analista": p.analista.nome if p.analista else None,
        }
        for p in propostas
    ]


@router.post("/{proposta_id}/revisar")
async def revisar_proposta(
    proposta_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Analista revisa proposta.

    Body: {status, observacao?, valor_sugerido?}
    status ∈ coord_revisao | reprovado
    """
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta:
        raise HTTPException(404, "Proposta não encontrada")

    if proposta.status != PropostaStatus.DRAFT:
        raise HTTPException(400, f"Proposta em status '{proposta.status}' não pode ser revisada")

    proposta.status = body.get("status", PropostaStatus.ANALISTA_REVISAO)
    proposta.analista_id = user.id

    if body.get("valor_sugerido"):
        proposta.valor_recomendado = Decimal(str(body["valor_sugerido"]))

    db.commit()

    return {
        "ok": True,
        "proposta_id": proposta.id,
        "status": proposta.status.value,
        "analista": user.nome or user.email,
    }


@router.post("/{proposta_id}/coordenador-revisar")
async def coord_revisar(
    proposta_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Coordenador revisa proposta."""
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta:
        raise HTTPException(404, "Proposta não encontrado")

    if proposta.status != PropostaStatus.ANALISTA_REVISAO:
        raise HTTPException(400, "Proposta não está em revisão de analista")

    proposta.status = body.get("status", PropostaStatus.COORD_REVISAO)
    proposta.coord_id = user.id
    proposta.coord_aprovado_em = datetime.utcnow()

    db.commit()

    return {"ok": True, "status": proposta.status.value}


@router.post("/{proposta_id}/aprovar")
async def aprovar_proposta(
    proposta_id: int,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Master aprova proposta e enfileira protocolo.

    Body: {valor_final?, motivo_edicao?, complexidade_ajustada?}
    """
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta:
        raise HTTPException(404, "Proposta não encontrada")

    if proposta.status not in (PropostaStatus.COORD_REVISAO, PropostaStatus.MASTER_REVISAO):
        raise HTTPException(400, f"Proposta em status '{proposta.status}' não pode ser aprovada")

    # Master aprova
    proposta.status = PropostaStatus.APROVADO
    proposta.master_id = user.id
    proposta.master_aprovado_em = datetime.utcnow()

    # Se mudou valor, registra feedback
    valor_final = body.get("valor_final")
    if valor_final and float(valor_final) != float(proposta.valor_recomendado or 0):
        feedback = PropostaFeedback(
            proposta_id=proposta.id,
            juiz=proposta.juiz,
            comarca=proposta.comarca,
            area_id=proposta.area_id,
            valor_proposto=proposta.valor_recomendado,
            valor_aprovado=Decimal(str(valor_final)),
            diferenca_pct=Decimal(str((float(valor_final) - float(proposta.valor_recomendado or 0)) / float(proposta.valor_recomendado or 1) * 100)),
            motivo=body.get("motivo_edicao", "Ajuste master"),
            motivo_texto_livre=body.get("motivo_texto", ""),
            master_id=user.id,
            master_nome=user.nome or user.email,
            complexidade_ajustada=body.get("complexidade_ajustada", False),
        )
        db.add(feedback)
        proposta.valor_recomendado = Decimal(str(valor_final))

    # Enfileira protocolo (Job)
    from app.models import Job
    job = Job(
        tipo="protocolo_proposta",
        status="na_fila",
        payload={
            "proposta_id": proposta.id,
            "processo_id": proposta.processo_id,
            "arquivo_docx": proposta.arquivo_docx_path,
            "numero_cnj": proposta.processo.numero_cnj if proposta.processo else None,
        }
    )
    db.add(job)
    proposta.status = PropostaStatus.PROTOCOLADO

    db.commit()

    return {
        "ok": True,
        "proposta_id": proposta.id,
        "status": proposta.status.value,
        "job_id": job.id,
        "valor_final": float(proposta.valor_recomendado or 0),
    }


@router.post("/{proposta_id}/rejeitar")
async def rejeitar_proposta(
    proposta_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Master rejeita proposta — volta para DRAFT."""
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta:
        raise HTTPException(404, "Proposta não encontrada")

    proposta.status = PropostaStatus.RECUSADO
    proposta.master_id = user.id
    proposta.master_motivo_rejeicao = body.get("motivo", "Rejeitado pelo master")

    db.commit()

    return {"ok": True, "proposta_id": proposta.id, "status": proposta.status.value}


@router.get("/{proposta_id}/download")
async def download_proposta(
    proposta_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Baixa DOCX da proposta."""
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta or not proposta.arquivo_docx_path:
        raise HTTPException(404, "Proposta/arquivo não encontrado")

    if not os.path.exists(proposta.arquivo_docx_path):
        raise HTTPException(404, "Arquivo não existe no servidor")

    return FileResponse(
        proposta.arquivo_docx_path,
        filename=os.path.basename(proposta.arquivo_docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@router.get("/juiz/{juiz_nome}/comparacao")
async def comparacao_juiz(
    juiz_nome: str,
    area_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Análise comparativa de propostas para um juiz.
    Identifica padrão de aprovação.
    """
    query = db.query(PropostaMotor).filter(
        PropostaMotor.juiz == juiz_nome,
        PropostaMotor.status == PropostaStatus.PROTOCOLADO,
    )

    if area_id:
        query = query.filter(PropostaMotor.area_id == area_id)

    propostas = query.limit(20).all()

    if not propostas:
        return {"juiz": juiz_nome, "total": 0, "propostas": []}

    valores = [float(p.valor_recomendado or 0) for p in propostas if p.valor_recomendado]
    media = sum(valores) / len(valores) if valores else 0
    min_val = min(valores) if valores else 0
    max_val = max(valores) if valores else 0

    return {
        "juiz": juiz_nome,
        "total": len(propostas),
        "media": media,
        "minimo": min_val,
        "maximo": max_val,
        "areas": [p.area_nome for p in propostas],
        "propostas": [
            {
                "processo": p.processo.numero_cnj if p.processo else None,
                "valor": float(p.valor_recomendado or 0),
                "area": p.area_nome,
            }
            for p in propostas[:5]
        ]
    }


@router.post("/feedback/{proposta_id}")
async def registrar_feedback(
    proposta_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Registra feedback de aprovação (já aprovada).
    Usado para aprendizado contínuo.

    Body: {valor_aprovado, motivo, complexidade_ajustada?}
    """
    proposta = db.query(PropostaMotor).get(proposta_id)
    if not proposta:
        raise HTTPException(404, "Proposta não encontrada")

    feedback = PropostaFeedback(
        proposta_id=proposta.id,
        juiz=proposta.juiz,
        comarca=proposta.comarca,
        area_id=proposta.area_id,
        valor_proposto=proposta.valor_recomendado,
        valor_aprovado=Decimal(str(body.get("valor_aprovado", proposta.valor_recomendado or 0))),
        motivo=body.get("motivo", "Feedback"),
        master_id=user.id,
        master_nome=user.nome or user.email,
        complexidade_ajustada=body.get("complexidade_ajustada", False),
    )
    db.add(feedback)
    db.commit()

    return {"ok": True, "feedback_id": feedback.id}


@router.get("/pendentes/dashboard")
async def dashboard_propostas(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard com alertas e status geral de propostas."""
    hoje = datetime.utcnow()
    dias_7 = hoje + timedelta(days=7)

    # Propostas vencidas
    vencidas = db.query(PropostaMotor).filter(
        and_(
            PropostaMotor.data_vencimento <= hoje,
            PropostaMotor.status != PropostaStatus.PROTOCOLADO,
        )
    ).count()

    # Propostas vencendo em 7 dias
    vencendo = db.query(PropostaMotor).filter(
        and_(
            PropostaMotor.data_vencimento.between(hoje, dias_7),
            PropostaMotor.status != PropostaStatus.PROTOCOLADO,
        )
    ).count()

    # Propostas por status
    por_status = {}
    for status in PropostaStatus:
        count = db.query(PropostaMotor).filter(PropostaMotor.status == status).count()
        por_status[status.value] = count

    # Propostas por área
    por_area = {}
    areas = db.query(PropostaMotor.area_nome, func.count(PropostaMotor.id)).group_by(
        PropostaMotor.area_nome
    ).all()
    for area_nome, count in areas:
        por_area[area_nome] = count

    return {
        "vencidas_urgente": vencidas,
        "vencendo_7_dias": vencendo,
        "por_status": por_status,
        "por_area": por_area,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Import Decimal no escopo do arquivo
from decimal import Decimal

