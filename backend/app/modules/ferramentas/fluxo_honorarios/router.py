"""Router for fluxo_honorarios (honorarium flow) — gerar ofício, registrar histórico juízo."""
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Processo, Oficio, Job, KanbanCartao, KanbanColuna, KanbanHistorico
from app.models.fluxo_honorarios import HistoricoJuiz
from app.services import get_db

from . import service
from .schemas import (
    JuizosImportBody,
    OficioGerarBody,
    DecidirBody,
    RegistrarAtuacaoBody,
    MarcaNuncaPagaBody,
)

router = APIRouter(prefix="/api/v1/fluxo-oficio", tags=["fluxo-oficio"])


@router.post("/gerar")
async def gerar(
    body: OficioGerarBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Decide E gera o ofício preenchido.

    Body: {processo_id, situacao, valor_proposto?, valor_arbitrado?, valor_majorado?,
    objeto?, prestador?, intimacao_id?}
    """
    if not body.processo_id:
        raise HTTPException(400, "processo_id é obrigatório")
    try:
        return service.gerar_oficio_honorarios(
            db,
            processo_id=body.processo_id,
            situacao=body.situacao,
            valor_proposto=body.valor_proposto,
            valor_arbitrado=body.valor_arbitrado,
            valor_majorado=body.valor_majorado,
            objeto=body.objeto,
            prestador=body.prestador,
            intimacao_id=body.intimacao_id,
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.post("/juiz/importar")
async def importar_juizes(
    body: JuizosImportBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Importa/agrega o histórico dos JUÍZOS (comarca+vara) varrido do acervo de ofícios.

    Marca nunca_paga quando declinamos >= 3 (padrão de juízo que impõe condição ruim).
    """
    juizos = body.juizos or []
    n = 0
    for j in juizos:
        slug = service._slug_juizo(j.comarca, j.vara)
        if not slug:
            continue
        h = db.query(HistoricoJuiz).filter(HistoricoJuiz.juiz_slug == slug).first()
        if not h:
            h = HistoricoJuiz(
                juiz_slug=slug,
                juiz_nome=f"{j.vara or '?'}, {j.comarca or '?'}",
                comarca=j.comarca,
                vara=j.vara,
                total_atuacoes=0,
                homologou=0,
                reduziu=0,
                declinamos=0,
            )
            db.add(h)
        prop, rat, dec = int(j.proposta or 0), int(j.ratifica or 0), int(j.declina or 0)
        # SET (idempotente) — o job manda o acumulado; reenviar não duplica
        h.total_atuacoes = prop + rat + dec
        h.reduziu = rat  # ratifica = houve tentativa de redução
        h.declinamos = dec
        h.nunca_paga = dec >= 3  # padrão de juízo que impõe condição ruim
        n += 1
    db.commit()
    total = db.query(HistoricoJuiz).count()
    return {"ok": True, "processados": n, "total_juizos": total}


@router.get("/pendentes")
async def pendentes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ofícios gerados aguardando APROVAÇÃO (antes do protocolo A3)."""
    ofs = (
        db.query(Oficio)
        .filter(Oficio.status == "gerado")
        .order_by(Oficio.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for o in ofs:
        p = o.processo
        out.append(
            {
                "oficio_id": o.id,
                "tipo": o.tipo,
                "status": o.status,
                "processo_id": o.processo_id,
                "numero_cnj": p.numero_cnj if p else None,
                "juiz": p.juiz if p else None,
                "vara": p.vara if p else None,
                "criado_em": o.created_at.isoformat() if o.created_at else None,
            }
        )
    return out


@router.post("/oficio/{oficio_id}/aprovar")
async def aprovar(
    oficio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aprova o ofício e ENFILEIRA o protocolo A3 (agente Windows converte docx→pdf e protocola)."""
    o = db.query(Oficio).get(oficio_id)
    if not o:
        raise HTTPException(404, "ofício não encontrado")
    if o.status not in ("gerado", "reprovado", "aguardando_revisao", "revisor_assinou"):
        raise HTTPException(400, f"ofício em status '{o.status}' não pode ser aprovado")
    p = o.processo
    job = Job(
        tipo="protocolo_oficio",
        status="na_fila",
        payload={
            "intimacao_id": o.intimacao_id,
            "oficio_id": o.id,
            "numero_cnj": p.numero_cnj if p else None,
            "arquivo_path": o.arquivo_docx_path,
            "converter_para_pdf": True,  # agente Windows converte antes de protocolar
        },
    )
    db.add(job)
    o.status = "protocolo_enfileirado"

    # Move cartão kanban para coluna "Protocolo" se existir
    if o.cartao_id:
        cartao = db.query(KanbanCartao).get(o.cartao_id)
        if cartao:
            coluna_protocolo = db.query(KanbanColuna).filter(
                KanbanColuna.kanban_id == cartao.kanban_id, KanbanColuna.nome == "Protocolo"
            ).first()
            if coluna_protocolo:
                # Registra movimento no histórico
                hist = KanbanHistorico(
                    cartao_id=cartao.id,
                    coluna_anterior_id=cartao.coluna_id,
                    coluna_nova_id=coluna_protocolo.id,
                    tipo_acao="protocolo",
                    motivo=f"Ofício aprovado por {user.nome or user.email}",
                    movido_por_id=user.id,
                    movido_por_nome=user.nome or user.email,
                )
                db.add(hist)
                cartao.coluna_id = coluna_protocolo.id

    db.commit()
    db.refresh(job)
    return {"ok": True, "oficio_id": o.id, "job_id": job.id, "status": o.status}


@router.post("/oficio/{oficio_id}/reprovar")
async def reprovar(
    oficio_id: int,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reprova o ofício com motivo opcional."""
    o = db.query(Oficio).get(oficio_id)
    if not o:
        raise HTTPException(404, "ofício não encontrado")
    o.status = "reprovado"
    if body.get("motivo"):
        o.erros = body["motivo"]
    db.commit()
    return {"ok": True, "oficio_id": o.id, "status": o.status}


@router.get("/oficio/{oficio_id}/download")
async def download(
    oficio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download do arquivo DOCX do ofício."""
    of = db.query(Oficio).get(oficio_id)
    if not of or not of.arquivo_docx_path or not os.path.exists(of.arquivo_docx_path):
        raise HTTPException(404, "ofício/arquivo não encontrado")
    return FileResponse(
        of.arquivo_docx_path,
        filename=os.path.basename(of.arquivo_docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/decidir")
async def decidir(
    body: DecidirBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Decide honorários: proposta | impugnacao | pagamento_ao_final."""
    processo_id = body.processo_id
    proc = db.query(Processo).get(processo_id) if processo_id else None
    juiz = body.juiz_nome or (proc.juiz if proc else None)
    return service.decidir_honorarios(
        db,
        processo_id=processo_id,
        juiz_nome=juiz,
        situacao=body.situacao,
        valor_proposto=body.valor_proposto,
        valor_arbitrado=body.valor_arbitrado,
    )


@router.get("/juizes")
async def listar_juizes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista histórico de juízos com estatísticas."""
    js = (
        db.query(HistoricoJuiz)
        .order_by(HistoricoJuiz.total_atuacoes.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": h.id,
            "juiz_nome": h.juiz_nome,
            "comarca": h.comarca,
            "vara": h.vara,
            "total_atuacoes": h.total_atuacoes,
            "homologou": h.homologou,
            "reduziu": h.reduziu,
            "declinamos": h.declinamos,
            "reducao_media_pct": float(h.reducao_media_pct) if h.reducao_media_pct is not None else None,
            "nunca_paga": h.nunca_paga,
        }
        for h in js
    ]


@router.post("/juiz/registrar")
async def registrar(
    body: RegistrarAtuacaoBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Registra o desfecho de uma atuação (constrói o histórico do juízo)."""
    if not body.juiz_nome:
        raise HTTPException(400, "juiz_nome é obrigatório")
    h = service.registrar_atuacao(
        db,
        juiz_nome=body.juiz_nome,
        comarca=body.comarca,
        vara=body.vara,
        reduziu=body.reduziu,
        reducao_pct=body.reducao_pct,
        homologou=body.homologou,
        declinamos=body.declinamos,
    )
    return {"ok": True, "juiz": h.juiz_nome, "total_atuacoes": h.total_atuacoes}


@router.patch("/juiz/{juiz_id}/nunca-paga")
async def marcar_nunca_paga(
    juiz_id: int,
    body: MarcaNuncaPagaBody = Body(default=MarcaNuncaPagaBody()),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Marca juízo como nunca_paga."""
    h = db.query(HistoricoJuiz).get(juiz_id)
    if not h:
        raise HTTPException(404, "juiz não encontrado")
    h.nunca_paga = bool(body.nunca_paga)
    db.commit()
    return {"ok": True, "juiz": h.juiz_nome, "nunca_paga": h.nunca_paga}
