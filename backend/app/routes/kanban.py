"""Kanban do perito logado: colunas, cartões e movimentação com histórico."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import User
from app.models.kanban import Kanban, KanbanColuna, KanbanCartao, KanbanHistorico
from app.seed import KANBAN_COLUNAS_PADRAO
from app.services import get_db
from app.middleware import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class CartaoCreate(BaseModel):
    titulo: str
    descricao: str | None = None
    quadro_id: int | None = None


class CartaoMover(BaseModel):
    coluna_id: int
    motivo: str | None = None


class CartaoProtocolo(BaseModel):
    protocolo_numero: str


def _get_or_create_kanban(db: Session, user: User) -> Kanban:
    kanban = db.query(Kanban).filter(Kanban.perito_id == user.id).first()
    if not kanban:
        kanban = Kanban(perito_id=user.id, nome="Meu Kanban")
        db.add(kanban)
        db.flush()
        for nome, posicao, cor in KANBAN_COLUNAS_PADRAO:
            db.add(KanbanColuna(kanban_id=kanban.id, nome=nome, posicao=posicao, cor=cor))
        db.commit()
        db.refresh(kanban)
    return kanban


@router.get("/quadros")
async def listar_quadros(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista os quadros (boards) do perito. Cria o primeiro se não houver."""
    _get_or_create_kanban(db, user)
    quadros = db.query(Kanban).filter(Kanban.perito_id == user.id).order_by(Kanban.id).all()
    return [
        {"id": q.id, "nome": q.nome,
         "cartoes": db.query(KanbanCartao).filter(KanbanCartao.kanban_id == q.id).count()}
        for q in quadros
    ]


class QuadroCreate(BaseModel):
    nome: str


@router.post("/quadros")
async def criar_quadro(
    payload: QuadroCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        kanban = Kanban(perito_id=user.id, nome=payload.nome.strip() or "Novo quadro")
        db.add(kanban)
        db.flush()
        for nome, posicao, cor in KANBAN_COLUNAS_PADRAO:
            db.add(KanbanColuna(kanban_id=kanban.id, nome=nome, posicao=posicao, cor=cor))
        db.commit()
        db.refresh(kanban)
        return {"id": kanban.id, "nome": kanban.nome}
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar quadro para usuario {user.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao criar quadro")


@router.get("/me")
async def meu_kanban(
    quadro_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if quadro_id:
        kanban = db.query(Kanban).filter(Kanban.id == quadro_id, Kanban.perito_id == user.id).first()
        if not kanban:
            raise HTTPException(status_code=404, detail="Quadro não encontrado")
    else:
        kanban = _get_or_create_kanban(db, user)
    colunas = (
        db.query(KanbanColuna)
        .filter(KanbanColuna.kanban_id == kanban.id)
        .order_by(KanbanColuna.posicao)
        .all()
    )
    return {
        "kanban": {"id": kanban.id, "nome": kanban.nome},
        "colunas": [
            {
                "id": col.id,
                "nome": col.nome,
                "cor": col.cor,
                "posicao": col.posicao,
                "cartoes": [
                    {
                        "id": c.id,
                        "titulo": c.titulo,
                        "descricao": c.descricao,
                        "status_revisao": c.status_revisao,
                        "protocolo_numero": c.protocolo_numero,
                        "processo_cnj": c.processo.numero_cnj if c.processo else None,
                    }
                    for c in sorted(col.cartoes, key=lambda c: c.posicao or 0)
                    if c.kanban_id == kanban.id
                ],
            }
            for col in colunas
        ],
    }


@router.post("/cartoes")
async def criar_cartao(
    payload: CartaoCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.quadro_id:
        kanban = db.query(Kanban).filter(Kanban.id == payload.quadro_id, Kanban.perito_id == user.id).first()
        if not kanban:
            raise HTTPException(status_code=404, detail="Quadro não encontrado")
    else:
        kanban = _get_or_create_kanban(db, user)
    primeira_coluna = (
        db.query(KanbanColuna)
        .filter(KanbanColuna.kanban_id == kanban.id)
        .order_by(KanbanColuna.posicao)
        .first()
    )
    if not primeira_coluna:
        raise HTTPException(status_code=500, detail="Kanban sem colunas")

    cartao = KanbanCartao(
        kanban_id=kanban.id,
        coluna_id=primeira_coluna.id,
        titulo=payload.titulo,
        descricao=payload.descricao,
        status_revisao="em_rascunho",
    )
    db.add(cartao)
    db.commit()
    db.refresh(cartao)
    return {"id": cartao.id, "titulo": cartao.titulo, "coluna_id": cartao.coluna_id}


@router.patch("/cartoes/{cartao_id}/mover")
async def mover_cartao(
    cartao_id: int,
    payload: CartaoMover,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kanban = _get_or_create_kanban(db, user)
    cartao = (
        db.query(KanbanCartao)
        .filter(KanbanCartao.id == cartao_id, KanbanCartao.kanban_id == kanban.id)
        .first()
    )
    if not cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    coluna_nova = (
        db.query(KanbanColuna)
        .filter(KanbanColuna.id == payload.coluna_id, KanbanColuna.kanban_id == kanban.id)
        .first()
    )
    if not coluna_nova:
        raise HTTPException(status_code=404, detail="Coluna não encontrada")

    db.add(KanbanHistorico(
        cartao_id=cartao.id,
        coluna_anterior_id=cartao.coluna_id,
        coluna_nova_id=coluna_nova.id,
        motivo=payload.motivo,
        tipo_acao="mover",
        movido_por_id=user.id,
        movido_por_nome=user.full_name,
    ))
    cartao.coluna_id = coluna_nova.id
    db.commit()

    # Aviso estilo SEI ao entrar em Revisão / Protocolo: checa pagamento/nota
    aviso = _aviso_revisao_protocolo(db, cartao, coluna_nova)
    return {"id": cartao.id, "coluna_id": cartao.coluna_id, "aviso": aviso}


def _aviso_revisao_protocolo(db: Session, cartao, coluna) -> dict | None:
    """Quando o cartão entra em Revisão/Protocolo, monta o aviso pro operador:
    já está pago? é judicial? tem comprovante? tem nota? — do processo ligado."""
    nome = (coluna.nome or "").lower()
    if "revis" not in nome and "protocol" not in nome:
        return None

    from app.models import Processo, NotaFiscal
    proc = db.query(Processo).filter(Processo.id == cartao.processo_id).first() if cartao.processo_id else None
    if not proc:
        return {
            "titulo": f"Cartão em '{coluna.nome}'",
            "sem_processo": True,
            "mensagem": "Este cartão não está ligado a um processo. Vincule para o sistema conferir pagamento, tipo e nota.",
        }
    nota = db.query(NotaFiscal).filter(NotaFiscal.processo_id == proc.id, NotaFiscal.status != "cancelada").first()
    checagens = [
        ("Pago?", "✅ Sim" if proc.pago else "❌ Não"),
        ("Forma de recebimento", proc.forma_recebimento or "não informada"),
        ("Judicial?", "Sim" if (proc.tipo or "").lower() == "judicial" else (proc.tipo or "—")),
        ("Nota fiscal", ("emitida" if nota and nota.status == "emitida" else (nota.status if nota else "sem nota"))),
        ("Honorários", f"R$ {float(proc.honorarios):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if proc.honorarios else "—"),
    ]
    # sugestão de ação (regra)
    sugestao = None
    if not proc.pago and (proc.tipo or "").lower() == "judicial":
        sugestao = "Judicial e NÃO pago → gerar ofício de entrega de laudo + pedido de pagamento."
    elif not proc.pago:
        sugestao = "Não pago → cobrar antes/depois do protocolo."

    # Qwen ANALISA o processo primeiro (assíncrono) e conclui/pergunta — o front busca o job
    from app.models import Job, Intimacao
    intim = db.query(Intimacao).filter(Intimacao.processo_id == proc.id).count()
    resumo = (f"Processo {proc.numero_cnj}. Tipo: {proc.tipo or 'não informado'}. "
              f"Pago: {'sim' if proc.pago else 'não'}. Forma: {proc.forma_recebimento or 'n/i'}. "
              f"Honorários: {proc.honorarios or 0}. Nota: {(nota.status if nota else 'sem nota')}. "
              f"Intimações: {intim}. Coluna destino: {coluna.nome}.")
    job = Job(tipo="analisar_cartao", status="na_fila",
              payload={"resumo": resumo, "cartao_id": cartao.id})
    db.add(job); db.commit(); db.refresh(job)

    return {
        "titulo": f"Conferência ao entrar em '{coluna.nome}'",
        "processo": proc.numero_cnj,
        "checagens": [{"item": k, "valor": v} for k, v in checagens],
        "sugestao": sugestao,
        "analise_job_id": job.id,
    }


class Devolver(BaseModel):
    coluna_id: int
    motivo: str


@router.patch("/cartoes/{cartao_id}/devolver")
async def devolver_cartao(
    cartao_id: int,
    payload: Devolver,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Estilo SEI: devolve o cartão a uma etapa anterior COM motivo obrigatório,
    e o registro fica gravado no histórico (auditável)."""
    if not payload.motivo.strip():
        raise HTTPException(status_code=400, detail="Informe o motivo da devolução (obrigatório)")
    kanban = _get_or_create_kanban(db, user)
    cartao = db.query(KanbanCartao).filter(
        KanbanCartao.id == cartao_id, KanbanCartao.kanban_id == kanban.id).first()
    if not cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")
    coluna = db.query(KanbanColuna).filter(
        KanbanColuna.id == payload.coluna_id, KanbanColuna.kanban_id == kanban.id).first()
    if not coluna:
        raise HTTPException(status_code=404, detail="Coluna não encontrada")
    db.add(KanbanHistorico(
        cartao_id=cartao.id, coluna_anterior_id=cartao.coluna_id,
        coluna_nova_id=coluna.id, motivo=payload.motivo, tipo_acao="devolver",
        movido_por_id=user.id, movido_por_nome=user.full_name,
    ))
    cartao.coluna_id = coluna.id
    db.commit()
    return {"ok": True}


@router.get("/cartoes/{cartao_id}/historico")
async def historico_cartao(
    cartao_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trilha de auditoria do cartão: cada movimento/devolução, quem e quando."""
    hist = db.query(KanbanHistorico).filter(
        KanbanHistorico.cartao_id == cartao_id).order_by(KanbanHistorico.id.desc()).all()
    colunas = {c.id: c.nome for c in db.query(KanbanColuna).all()}
    return [
        {
            "id": h.id, "tipo_acao": h.tipo_acao,
            "de": colunas.get(h.coluna_anterior_id), "para": colunas.get(h.coluna_nova_id),
            "motivo": h.motivo, "por": h.movido_por_nome,
            "quando": h.created_at.isoformat() if h.created_at else None,
        }
        for h in hist
    ]


@router.patch("/cartoes/{cartao_id}/protocolo")
async def registrar_protocolo(
    cartao_id: int,
    payload: CartaoProtocolo,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Registro manual do número de protocolo REAL obtido no ESAJ/PJe.

    Enquanto o protocolo automático não é homologado com o tribunal, este é o
    único caminho que grava protocolo_numero — nunca um número inventado.
    """
    from datetime import datetime

    kanban = _get_or_create_kanban(db, user)
    cartao = (
        db.query(KanbanCartao)
        .filter(KanbanCartao.id == cartao_id, KanbanCartao.kanban_id == kanban.id)
        .first()
    )
    if not cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    cartao.protocolo_numero = payload.protocolo_numero.strip()
    cartao.protocolado_em = datetime.utcnow()
    cartao.status_revisao = "protocolado"
    db.commit()
    return {"id": cartao.id, "protocolo_numero": cartao.protocolo_numero}
