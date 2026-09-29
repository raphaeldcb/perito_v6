"""Protocolo — documentos revisados a protocolar (imediato ou em lote)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, ItemProtocolo, Job, Processo
from app.services import get_db
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/protocolo", tags=["protocolo"])

TIPOS_PADRAO = ["oficio", "manifestacao", "laudo", "outro"]


class NovoItem(BaseModel):
    processo_id: int | None = None
    numero_processo: str | None = None
    cartao_id: int | None = None
    tipo_documento: str = "oficio"       # oficio, manifestacao, laudo, outro
    nome_documento: str
    caminho: str | None = None
    revisado: bool = True                # o sistema só envia se revisado = sim
    modo: str = "lote"                   # imediato | lote


def _enfileirar_protocolo(db: Session, item: ItemProtocolo):
    """Manda o documento para o protocolo (job no agente Mac)."""
    item.status = "protocolando"
    db.add(Job(tipo="protocolo", status="na_fila", payload={
        "item_protocolo_id": item.id, "numero_cnj": item.numero_processo,
        "laudo_docx_path": item.caminho, "tribunal": "TJMS", "cartao_id": item.cartao_id,
    }))


@router.post("/itens")
async def adicionar(payload: NovoItem, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Adiciona um documento revisado à fila de protocolo. Se modo=imediato,
    já dispara o protocolo; se lote, fica aguardando para protocolar em conjunto."""
    if not payload.revisado:
        raise HTTPException(status_code=400, detail="O documento precisa estar revisado para protocolar.")
    cnj = payload.numero_processo
    if not cnj and payload.processo_id:
        proc = db.query(Processo).filter(Processo.id == payload.processo_id).first()
        cnj = proc.numero_cnj if proc else None
    item = ItemProtocolo(
        processo_id=payload.processo_id, cartao_id=payload.cartao_id, numero_processo=cnj,
        tipo_documento=payload.tipo_documento, nome_documento=payload.nome_documento,
        caminho=payload.caminho, revisado=True, modo=payload.modo, status="na_fila",
    )
    db.add(item); db.commit(); db.refresh(item)
    if payload.modo == "imediato":
        _enfileirar_protocolo(db, item); db.commit()
    return {"id": item.id, "status": item.status, "modo": item.modo}


@router.get("/fila")
async def fila(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    itens = db.query(ItemProtocolo).filter(ItemProtocolo.status != "protocolado").order_by(
        ItemProtocolo.id.desc()).all()
    return [{
        "id": i.id, "numero_processo": i.numero_processo, "tipo_documento": i.tipo_documento,
        "nome_documento": i.nome_documento, "modo": i.modo, "status": i.status,
        "protocolo_numero": i.protocolo_numero,
    } for i in itens]


class ProtocolarLote(BaseModel):
    ids: list[int] = []   # vazio = todos os do lote em espera


@router.post("/protocolar-lote")
async def protocolar_lote(payload: ProtocolarLote, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Protocola de uma vez os documentos revisados em espera (lote)."""
    q = db.query(ItemProtocolo).filter(ItemProtocolo.status == "na_fila")
    if payload.ids:
        q = q.filter(ItemProtocolo.id.in_(payload.ids))
    else:
        q = q.filter(ItemProtocolo.modo == "lote")
    itens = q.all()
    for item in itens:
        _enfileirar_protocolo(db, item)
    db.commit()
    return {"protocolando": len(itens)}


class NumeroInput(BaseModel):
    protocolo_numero: str


@router.patch("/itens/{item_id}/numero")
async def registrar_numero(item_id: int, payload: NumeroInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Registra o número REAL do protocolo (manual, quando protocolado no e-SAJ)."""
    item = db.query(ItemProtocolo).filter(ItemProtocolo.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    item.protocolo_numero = payload.protocolo_numero
    item.status = "protocolado"
    db.commit()
    return {"ok": True}


@router.delete("/itens/{item_id}")
async def remover(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(ItemProtocolo).filter(ItemProtocolo.id == item_id).first()
    if item:
        db.delete(item); db.commit()
    return {"ok": True}
