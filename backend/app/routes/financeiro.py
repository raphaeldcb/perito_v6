"""Conciliação bancária: upload do extrato mensal → lançamentos → match
automático por nome com coletador/usuário; ajuste manual sempre disponível.
"""
import csv
import io
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.middleware import get_current_user
from app.models import User, Coletador, ExtratoBancario, LancamentoBancario
from app.models import DocumentoColetador
from app.routes.jobs import verificar_agente
from app.services import get_db
from app.services.conciliacao import conciliar_lancamento
from app.services.comprovante import gerar_comprovante_para_lancamento
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/financeiro", tags=["financeiro"])


def exigir_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name not in ("admin", "power_user"):
        raise HTTPException(status_code=403, detail="Sem permissão financeira")
    return user


def _parse_valor(txt: str) -> float:
    txt = (txt or "").strip().replace("R$", "").replace(".", "").replace(",", ".")
    txt = txt.replace(" ", "")
    try:
        return float(txt)
    except ValueError:
        return 0.0


def _parse_data(txt: str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime((txt or "").strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_ofx(texto: str) -> list[dict]:
    """Parser de OFX (formato SGML do Inter). Extrai data, valor, tipo, favorecido.

    Favorecido = <NAME> (nome do beneficiário); se vazio, usa <MEMO>.
    """
    import re as _re
    lancamentos = []
    for bloco in _re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, _re.DOTALL | _re.IGNORECASE):
        def campo(tag):
            m = _re.search(rf"<{tag}>([^<\r\n]*)", bloco, _re.IGNORECASE)
            return (m.group(1).strip() if m else "")

        valor_txt = campo("TRNAMT").replace(",", ".")
        try:
            valor = float(valor_txt)
        except ValueError:
            continue
        dt = campo("DTPOSTED")[:8]
        data = None
        if len(dt) == 8:
            try:
                data = datetime.strptime(dt, "%Y%m%d").date()
            except ValueError:
                pass
        nome = campo("NAME")
        memo = campo("MEMO")
        favorecido = nome or memo
        lancamentos.append({
            "data": data, "valor": valor, "favorecido": favorecido,
            "descricao": memo or nome, "tipo": campo("TRNTYPE"),
        })
    return lancamentos


def _mapear_colunas(fieldnames: list) -> dict:
    """Descobre quais colunas do CSV são data/descrição/valor (nomes variam por banco)."""
    m = {}
    for col in fieldnames or []:
        c = (col or "").strip().lower()
        if not m.get("data") and ("data" in c or "date" in c):
            m["data"] = col
        elif not m.get("descricao") and any(k in c for k in ["descri", "histor", "lançamento", "lancamento", "favorec", "beneficiar", "memo"]):
            m["descricao"] = col
        elif not m.get("valor") and ("valor" in c or "amount" in c or "value" in c):
            m["valor"] = col
    return m


@router.post("/extrato")
async def upload_extrato(
    competencia: str = Form(...),
    banco: str = Form(""),
    empresa_id: int = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Recebe extrato CSV, cria lançamentos e concilia automaticamente por nome."""
    conteudo = await file.read()
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")

    nome_lower = (file.filename or "").lower()
    eh_ofx = nome_lower.endswith(".ofx") or "<STMTTRN>" in texto.upper()

    # normaliza tudo para uma lista de dicts {data, valor, favorecido, descricao}
    registros = []
    if eh_ofx:
        registros = _parse_ofx(texto)
        if not registros:
            raise HTTPException(status_code=400, detail="OFX sem transações reconhecíveis")
    else:
        try:
            dialect = csv.Sniffer().sniff(texto[:2048], delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(texto), dialect=dialect)
        mapa = _mapear_colunas(reader.fieldnames)
        if not mapa.get("valor") or not mapa.get("descricao"):
            raise HTTPException(
                status_code=400,
                detail=f"Não identifiquei as colunas de valor/descrição. Colunas: {reader.fieldnames}",
            )
        for linha in reader:
            descricao = (linha.get(mapa["descricao"]) or "").strip()
            valor = _parse_valor(linha.get(mapa["valor"]))
            if not descricao and not valor:
                continue
            registros.append({
                "data": _parse_data(linha.get(mapa.get("data", ""), "")),
                "valor": valor, "favorecido": descricao, "descricao": descricao,
            })

    # salva o arquivo original
    base = os.path.join(settings.storage_dir, "extratos")
    os.makedirs(base, exist_ok=True)
    arquivo_path = os.path.join(base, f"{competencia}_{file.filename}")
    with open(arquivo_path, "wb") as f:
        f.write(conteudo)

    extrato = ExtratoBancario(
        empresa_id=empresa_id or None, banco=banco, competencia=competencia,
        arquivo_path=arquivo_path,
    )
    db.add(extrato)
    db.flush()

    # carrega alvos do match uma vez
    coletadores = [(c.id, c.nome_completo, c.apelido) for c in db.query(Coletador).filter(Coletador.ativo == True).all()]
    usuarios = [(u.id, u.full_name) for u in db.query(User).all()]

    total, conciliados = 0, 0
    for reg in registros:
        descricao = reg["favorecido"]
        valor = reg["valor"]
        data = reg["data"]
        tipo_mov = "credito" if valor >= 0 else "debito"

        lanc = LancamentoBancario(
            extrato_id=extrato.id, data=data, descricao=reg.get("descricao") or descricao,
            favorecido=descricao, valor=abs(valor), tipo=tipo_mov,
        )
        # concilia por nome (só faz sentido em saídas/pagamentos, mas tenta em todos)
        tipo, alvo_id, score = conciliar_lancamento(descricao, coletadores, usuarios)
        lanc.match_score = score
        if tipo == "coletador":
            lanc.coletador_id = alvo_id
            lanc.status = "conciliado"
            conciliados += 1
        elif tipo == "usuario":
            lanc.usuario_id = alvo_id
            lanc.status = "conciliado"
            conciliados += 1
        db.add(lanc)
        db.flush()
        # gera o comprovante em PDF no portal do coletador casado (saídas)
        if lanc.coletador_id and lanc.tipo == "debito":
            gerar_comprovante_para_lancamento(db, lanc)
        total += 1

    extrato.total_lancamentos = total
    extrato.total_conciliados = conciliados
    db.commit()
    return {
        "extrato_id": extrato.id, "competencia": competencia,
        "total_lancamentos": total, "conciliados_automaticamente": conciliados,
        "pendentes": total - conciliados,
    }


@router.get("/extratos")
async def listar_extratos(db: Session = Depends(get_db), user: User = Depends(exigir_admin)):
    ex = db.query(ExtratoBancario).order_by(ExtratoBancario.id.desc()).all()
    return [
        {"id": e.id, "competencia": e.competencia, "banco": e.banco,
         "total": e.total_lancamentos, "conciliados": e.total_conciliados}
        for e in ex
    ]


@router.get("/extrato/{extrato_id}/lancamentos")
async def lancamentos(
    extrato_id: int,
    status: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista lançamentos de um extrato. Qualquer usuário pode ver (não só admin)."""
    # Verificar se extrato existe
    extrato = db.query(ExtratoBancario).filter(ExtratoBancario.id == extrato_id).first()
    if not extrato:
        raise HTTPException(status_code=404, detail="Extrato não encontrado")

    q = db.query(LancamentoBancario).filter(LancamentoBancario.extrato_id == extrato_id)
    if status:
        q = q.filter(LancamentoBancario.status == status)
    itens = q.order_by(LancamentoBancario.data).all()

    # nomes dos alvos casados
    col_ids = {l.coletador_id for l in itens if l.coletador_id}
    cols = {c.id: c.nome_completo for c in db.query(Coletador).filter(Coletador.id.in_(col_ids)).all()} if col_ids else {}

    return [
        {
            "id": l.id, "data": l.data.isoformat() if l.data else None,
            "favorecido": l.favorecido, "valor": float(l.valor) if l.valor else 0,
            "tipo": l.tipo, "status": l.status,
            "match_score": float(l.match_score) if l.match_score else 0,
            "match_manual": l.match_manual,
            "coletador_id": l.coletador_id,
            "coletador_nome": cols.get(l.coletador_id),
            "usuario_id": l.usuario_id,
        }
        for l in itens
    ]


class ConciliarManual(BaseModel):
    coletador_id: int | None = None
    usuario_id: int | None = None
    status: str | None = None  # conciliado | ignorado | pendente


@router.patch("/lancamento/{lancamento_id}")
async def conciliar_manual(
    lancamento_id: int,
    payload: ConciliarManual,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Ajuste manual — Bruno e alguns recebem por outras formas, então dá pra
    casar/ignorar/reatribuir qualquer lançamento à mão."""
    l = db.query(LancamentoBancario).filter(LancamentoBancario.id == lancamento_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    if payload.coletador_id is not None:
        l.coletador_id = payload.coletador_id or None
        l.usuario_id = None
        l.status = "conciliado" if payload.coletador_id else "pendente"
        l.match_manual = True
        if l.coletador_id:
            db.flush()
            gerar_comprovante_para_lancamento(db, l)
    if payload.usuario_id is not None:
        l.usuario_id = payload.usuario_id or None
        l.coletador_id = None
        l.status = "conciliado" if payload.usuario_id else "pendente"
        l.match_manual = True
    if payload.status:
        l.status = payload.status

    # recalcula total conciliado do extrato
    extrato = db.query(ExtratoBancario).filter(ExtratoBancario.id == l.extrato_id).first()
    if extrato:
        extrato.total_conciliados = db.query(LancamentoBancario).filter(
            LancamentoBancario.extrato_id == extrato.id,
            LancamentoBancario.status == "conciliado",
        ).count()
    db.commit()
    return {"ok": True, "status": l.status}


# ---- Sincronização dos comprovantes para a pasta CONVENIADOS (agente Mac) ----
@router.get("/comprovantes/sync-lista")
async def comprovantes_sync_lista(db: Session = Depends(get_db), _=Depends(verificar_agente)):
    """Lista os comprovantes com PDF, para o agente Mac copiar à pasta do OneDrive.
    O nome do arquivo já vem no padrão SCPG (ex: 297.26.01.pdf)."""
    import os
    docs = db.query(DocumentoColetador).filter(
        DocumentoColetador.tipo == "comprovante",
        DocumentoColetador.arquivo_path.isnot(None),
    ).all()
    return [
        {"doc_id": d.id, "filename": os.path.basename(d.arquivo_path)}
        for d in docs if d.arquivo_path
    ]


@router.get("/comprovantes/{doc_id}/arquivo")
async def comprovante_arquivo(doc_id: int, db: Session = Depends(get_db), _=Depends(verificar_agente)):
    import os
    from fastapi.responses import FileResponse
    d = db.query(DocumentoColetador).filter(DocumentoColetador.id == doc_id).first()
    if not d or not d.arquivo_path or not os.path.exists(d.arquivo_path):
        raise HTTPException(status_code=404, detail="Comprovante não encontrado")
    return FileResponse(d.arquivo_path, filename=os.path.basename(d.arquivo_path))
