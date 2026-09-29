"""Gerência financeira — consolida receita × despesa + produção por relator."""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.middleware import get_current_user
from app.models import User, Despesa
from app.services import get_db
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/gerencia", tags=["gerencia"])


@router.get("/")
async def gerencia_root(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Root gerencia endpoint — returns quick financial summary."""
    rec = db.execute(text("SELECT COALESCE(SUM(valor),0) FROM receita")).scalar()
    desp = db.execute(text("SELECT COALESCE(SUM(valor),0) FROM despesa")).scalar()
    return {
        "status": "ok",
        "receita_total": float(rec),
        "despesa_total": float(desp),
        "saldo": float(rec) - float(desp),
        "endpoints": ["/dashboard", "/receitas", "/despesas"]
    }


@router.get("/dashboard")
async def dashboard(ano: int = Query(..., ge=2000, le=2100),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = db.execute(text("SELECT COALESCE(SUM(valor),0) FROM receita WHERE ano=:a"), {"a": ano}).scalar()
    desp = db.execute(text("SELECT COALESCE(SUM(valor),0) FROM despesa WHERE ano=:a"), {"a": ano}).scalar()
    por_mes = [
        {"mes": m,
         "receita": float(db.execute(text("SELECT COALESCE(SUM(valor),0) FROM receita WHERE ano=:a AND mes=:m"), {"a": ano, "m": m}).scalar()),
         "despesa": float(db.execute(text("SELECT COALESCE(SUM(valor),0) FROM despesa WHERE ano=:a AND mes=:m"), {"a": ano, "m": m}).scalar())}
        for m in range(1, 13)
    ]
    por_setor = [{"setor": r[0] or "OUTRO", "valor": float(r[1])} for r in db.execute(
        text("SELECT setor, SUM(valor) FROM receita WHERE ano=:a GROUP BY setor ORDER BY 2 DESC"), {"a": ano})]
    por_categoria = [{"categoria": r[0] or "OUTRO", "valor": float(r[1])} for r in db.execute(
        text("SELECT categoria, SUM(valor) FROM despesa WHERE ano=:a AND valor IS NOT NULL GROUP BY categoria ORDER BY 2 DESC"), {"a": ano})]
    return {"ano": ano, "receita_total": float(rec), "despesa_total": float(desp),
            "saldo": float(rec) - float(desp), "por_mes": por_mes,
            "por_setor": por_setor, "por_categoria": por_categoria}


@router.get("/receitas")
async def receitas(ano: int = 0, setor: str = "", origem: str = "", limit: int = 100, offset: int = 0,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    where, p = ["1=1"], {}
    if ano: where.append("ano=:a"); p["a"] = ano
    if setor: where.append("setor=:s"); p["s"] = setor
    if origem: where.append("origem=:o"); p["o"] = origem
    w = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM receita WHERE {w}"), p).scalar()
    rows = db.execute(text(f"SELECT id,data,ano,mes,setor,valor,tipo_pagamento,descricao,origem,forma_liquidacao,forma_pagamento,conta,tem_nf FROM receita WHERE {w} ORDER BY data DESC NULLS LAST, id DESC LIMIT :l OFFSET :of"),
                      {**p, "l": limit, "of": offset})
    itens = [dict(r._mapping) | {"valor": float(r.valor), "data": str(r.data) if r.data else None} for r in rows]
    return {"total": total, "itens": itens}


@router.get("/despesas")
async def despesas(ano: int = 0, categoria: str = "", pago: str = "", limit: int = 100, offset: int = 0,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    where, p = ["1=1"], {}
    if ano: where.append("ano=:a"); p["a"] = ano
    if categoria: where.append("categoria=:c"); p["c"] = categoria
    if pago in ("true", "false"): where.append("pago=:pg"); p["pg"] = (pago == "true")
    w = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM despesa WHERE {w}"), p).scalar()
    rows = db.execute(text(f"SELECT id,fornecedor,data,vencimento,valor,categoria,status,pago,arquivo_path,descricao,recorrencia,forma_pagamento,conta,tem_nf FROM despesa WHERE {w} ORDER BY data DESC NULLS LAST, id DESC LIMIT :l OFFSET :of"),
                      {**p, "l": limit, "of": offset})
    itens = [dict(r._mapping) | {"valor": float(r.valor) if r.valor is not None else None,
                                 "data": str(r.data) if r.data else None} for r in rows]
    return {"total": total, "itens": itens}


class DespesaIn(BaseModel):
    fornecedor: str | None = None
    data: str | None = None
    vencimento: str | None = None
    valor: float | None = None
    categoria: str | None = None
    descricao: str | None = None
    ano: int | None = None
    mes: int | None = None
    pago: bool = False
    recorrencia: str | None = None       # avulsa | mensal
    forma_pagamento: str | None = None   # dinheiro/cartao_credito/cartao_debito/pix/cheque
    conta: str | None = None             # ipc | externo
    tem_nf: bool | None = None


CAMPOS_DESPESA = ("fornecedor", "data", "vencimento", "valor", "categoria", "descricao",
                  "ano", "mes", "pago", "recorrencia", "forma_pagamento", "conta", "tem_nf")


@router.post("/despesas", status_code=201)
async def criar_despesa(body: DespesaIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = Despesa(fornecedor=body.fornecedor, data=body.data, vencimento=body.vencimento,
                valor=body.valor, categoria=body.categoria, descricao=body.descricao,
                ano=body.ano, mes=body.mes, pago=body.pago,
                status="pago" if body.pago else "a_pagar", origem="manual")
    db.add(d); db.commit(); db.refresh(d)
    return {"id": d.id}


@router.patch("/despesas/{despesa_id}")
async def editar_despesa(despesa_id: int, body: DespesaIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.query(Despesa).filter(Despesa.id == despesa_id).first()
    if not d:
        raise HTTPException(404, "despesa não encontrada")
    for campo in CAMPOS_DESPESA:
        v = getattr(body, campo)
        if v is not None:
            setattr(d, campo, v)
    d.status = "pago" if d.pago else "a_pagar"
    db.commit()
    return {"ok": True}


class ReceitaIn(BaseModel):
    forma_liquidacao: str | None = None   # a_vista/parcelado/conta_unica/ao_final
    forma_pagamento: str | None = None
    conta: str | None = None              # ipc | externo
    tem_nf: bool | None = None
    setor: str | None = None
    tipo_pagamento: str | None = None


@router.patch("/receitas/{receita_id}")
async def editar_receita(receita_id: int, body: ReceitaIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.models import Receita
    r = db.query(Receita).filter(Receita.id == receita_id).first()
    if not r:
        raise HTTPException(404, "receita não encontrada")
    for campo in ("forma_liquidacao", "forma_pagamento", "conta", "tem_nf", "setor", "tipo_pagamento"):
        v = getattr(body, campo)
        if v is not None:
            setattr(r, campo, v)
    db.commit()
    return {"ok": True}


@router.get("/conciliacao/resumo")
async def conciliacao_resumo(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.execute(text(
        "SELECT count(*) total, count(*) FILTER (WHERE status='conciliado') conciliados, "
        "count(receita_id) via_receita, count(despesa_id) via_despesa, "
        "round(sum(valor) FILTER (WHERE tipo='credit')) creditos, round(sum(valor) FILTER (WHERE tipo='debit')) debitos "
        "FROM lancamento_bancario")).first()
    total = row.total or 1
    return {"total": row.total, "conciliados": row.conciliados, "pendentes": row.total - row.conciliados,
            "pct": round(100.0 * row.conciliados / total, 1), "via_receita": row.via_receita,
            "via_despesa": row.via_despesa, "creditos": float(row.creditos or 0), "debitos": float(row.debitos or 0)}


@router.get("/regras")
async def listar_regras(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(text("SELECT id, nome, tipo, valor_mensal, percentual, dia_fechamento, dia_pagamento, paga_dia_util, aplicavel_a, ativa FROM regra_financeira ORDER BY id"))
    return [dict(r._mapping) | {"valor_mensal": float(r.valor_mensal) if r.valor_mensal is not None else None,
                                "percentual": float(r.percentual) if r.percentual is not None else None} for r in rows]


class RegraIn(BaseModel):
    nome: str | None = None
    tipo: str | None = None          # despesa_recorrente/rateio_honorario/terceirizado/conveniado
    valor_mensal: float | None = None
    percentual: float | None = None
    dia_fechamento: int | None = None
    dia_pagamento: int | None = None
    paga_dia_util: bool | None = None
    aplicavel_a: str | None = None
    ativa: bool | None = None


@router.post("/regras", status_code=201)
async def criar_regra(body: RegraIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.execute(text(
        "INSERT INTO regra_financeira (nome, tipo, valor_mensal, percentual, dia_fechamento, dia_pagamento, paga_dia_util, aplicavel_a, ativa) "
        "VALUES (:n,:t,:vm,:p,:df,:dp,:pu,:a,true) RETURNING id"),
        {"n": body.nome, "t": body.tipo, "vm": body.valor_mensal, "p": body.percentual,
         "df": body.dia_fechamento, "dp": body.dia_pagamento, "pu": bool(body.paga_dia_util), "a": body.aplicavel_a})
    db.commit()
    return {"id": r.scalar()}


@router.patch("/regras/{regra_id}")
async def editar_regra(regra_id: int, body: RegraIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campos = {k: v for k, v in body.model_dump().items() if v is not None}
    if not campos:
        return {"ok": True}
    sets = ", ".join(f"{k} = :{k}" for k in campos)
    db.execute(text(f"UPDATE regra_financeira SET {sets}, updated_at = now() WHERE id = :id"), {**campos, "id": regra_id})
    db.commit()
    return {"ok": True}


@router.post("/regras/{regra_id}/gerar")
async def gerar_recorrente(regra_id: int, ano: int = Query(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Gera 12 despesas mensais a partir de uma regra despesa_recorrente/terceirizado/conveniado."""
    r = db.execute(text("SELECT nome, tipo, valor_mensal, dia_pagamento, aplicavel_a FROM regra_financeira WHERE id=:id AND ativa"), {"id": regra_id}).first()
    if not r:
        raise HTTPException(404, "regra não encontrada ou inativa")
    valor = float(r.valor_mensal) if r.valor_mensal is not None else None
    dia = r.dia_pagamento or 1
    criadas = 0
    for mes in range(1, 13):
        dia_seguro = min(dia, 28)
        ref = f"regra{regra_id}-{ano}-{mes:02d}"
        res = db.execute(text(
            "INSERT INTO despesa (data, ano, mes, fornecedor, descricao, categoria, valor, status, pago, recorrencia, origem, origem_ref) "
            "VALUES (make_date(:a,:m,:d), :a, :m, :nome, :desc, :cat, :val, 'a_pagar', false, 'mensal', 'regra', :ref) "
            "ON CONFLICT (origem, origem_ref) DO NOTHING"),
            {"a": ano, "m": mes, "d": dia_seguro, "nome": r.nome, "desc": f"{r.nome} ({r.tipo}) — {mes:02d}/{ano}",
             "cat": r.aplicavel_a or r.tipo, "val": valor, "ref": ref})
        criadas += res.rowcount
    db.commit()
    return {"ok": True, "geradas": criadas, "ano": ano}


@router.get("/por-relator")
async def por_relator(ano: int = 0, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT relator_nome, COUNT(*) laudos, COALESCE(SUM(valor_pgto),0) valor "
        "FROM projetocp_laudo_relator GROUP BY relator_nome ORDER BY valor DESC"))
    return [{"relator": r[0], "laudos": r[1], "valor_pgto": float(r[2])} for r in rows]
