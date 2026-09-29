"""Ingestão do financeiro — recebe extratos/despesas já extraídos (DeepSeek/Qwen)
e cria ExtratoBancario+LancamentoBancario / Despesa. Idempotente (dedup por arquivo)."""
from datetime import datetime

from fastapi import APIRouter, Depends, Body
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, ExtratoBancario, LancamentoBancario
from app.models.despesa import Despesa
from app.services import get_db
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/financeiro", tags=["financeiro-ingest"])


def _data(s):
    if not s:
        return None
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(str(s)[:10], f).date()
        except ValueError:
            pass
    return None


@router.post("/extrato/ingerir-json")
async def ingerir_extrato(body: dict = Body(...), db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    arq = body.get("arquivo_path")
    if arq and db.query(ExtratoBancario).filter(ExtratoBancario.arquivo_path == arq).first():
        return {"skip": "ja ingerido", "arquivo": arq}
    transacoes = [t for t in (body.get("transacoes") or []) if t]
    if not transacoes:
        return {"skip": "sem transacoes"}
    comp = None
    for t in transacoes:
        d0 = _data(t.get("data"))
        if d0:
            comp = d0.strftime("%Y-%m"); break
    ext = ExtratoBancario(banco=(body.get("banco") or "")[:120], competencia=comp,
                          arquivo_path=arq, total_lancamentos=0)
    db.add(ext); db.flush()
    n = 0
    for t in transacoes:
        try:
            v = float(t.get("valor"))
        except (TypeError, ValueError):
            continue
        desc = (t.get("descricao") or "")
        db.add(LancamentoBancario(extrato_id=ext.id, data=_data(t.get("data")),
                                  descricao=desc, favorecido=desc[:200], valor=v,
                                  tipo="credito", status="pendente"))
        n += 1
    ext.total_lancamentos = n
    db.commit()
    return {"extrato_id": ext.id, "lancamentos": n}


@router.post("/despesa/ingerir-json")
async def ingerir_despesa(body: dict = Body(...), db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    arq = body.get("arquivo_path")
    if arq and db.query(Despesa).filter(Despesa.arquivo_path == arq).first():
        return {"skip": "ja ingerido"}
    try:
        v = float(body.get("valor"))
    except (TypeError, ValueError):
        return {"skip": "sem valor"}
    d = Despesa(fornecedor=(body.get("fornecedor") or "")[:200], data=_data(body.get("data")),
                vencimento=_data(body.get("vencimento")), valor=v,
                descricao=body.get("descricao"), categoria=(body.get("categoria") or "outro")[:40],
                arquivo_path=arq)
    db.add(d); db.commit()
    return {"despesa_id": d.id}


@router.get("/despesas")
async def listar_despesas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = db.query(Despesa).order_by(Despesa.data.desc().nullslast()).limit(400).all()
    return [{"id": x.id, "fornecedor": x.fornecedor, "data": x.data.isoformat() if x.data else None,
             "vencimento": x.vencimento.isoformat() if x.vencimento else None,
             "valor": float(x.valor) if x.valor else 0, "categoria": x.categoria,
             "status": x.status, "descricao": x.descricao} for x in ds]


@router.get("/resumo-financeiro")
async def resumo(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ent = db.query(func.count(LancamentoBancario.id),
                   func.coalesce(func.sum(LancamentoBancario.valor), 0)).filter(
        LancamentoBancario.tipo == "credito").first()
    des = db.query(func.count(Despesa.id), func.coalesce(func.sum(Despesa.valor), 0)).first()
    return {"entradas_qtd": ent[0], "entradas_total": float(ent[1] or 0),
            "despesas_qtd": des[0], "despesas_total": float(des[1] or 0),
            "saldo": float((ent[1] or 0) - (des[1] or 0))}
