"""Gera o ofício de honorários PREENCHIDO (proposta / ratifica / declina).

Junta o motor de decisão (qual template + NN) com o template real do IPC
(app/templates/honorarios/*.docx) e os dados do processo. Cria o registro Oficio.
"""
import logging
import os
from datetime import date, datetime

from app.models import Oficio, Processo, Intimacao
from app.services import fluxo_honorarios as motor
from app.services.oficio import valores_do_processo
from app.services.oficio_generator import _preencher_documento

logger = logging.getLogger(__name__)

TEMPLATE_FILE = {"proposta": "proposta.docx", "ratifica": "ratifica.docx", "declina": "declina.docx"}
AREA_COD = {"contábil": "10", "contabil": "10", "médica": "20", "medica": "20",
            "engenharia": "30", "grafotécnica": "40", "grafotecnica": "40",
            "avaliação": "60", "avaliacao": "60", "insalubridade": "65"}


def _valor_br(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return ""


def _extenso(v):
    if not v:
        return ""
    try:
        from num2words import num2words
        return num2words(float(v), lang="pt_BR", to="currency")
    except Exception:
        return _valor_br(v)


def _cod_area(esp):
    e = (esp or "").lower()
    for k, c in AREA_COD.items():
        if k in e:
            return c
    return "00"


def gerar_oficio_honorarios(db, processo_id, situacao, valor_proposto=None,
                            valor_arbitrado=None, valor_majorado=None, objeto=None,
                            prestador="47", intimacao_id=None) -> dict:
    proc = db.query(Processo).get(processo_id)
    if not proc:
        raise ValueError("processo não encontrado")
    if not intimacao_id:  # ofício nasce de uma intimação — pega a última do processo
        last = db.query(Intimacao).filter(Intimacao.processo_id == processo_id).order_by(
            Intimacao.id.desc()).first()
        intimacao_id = last.id if last else None
    if not intimacao_id:
        raise ValueError("processo sem intimação — informe intimacao_id")

    dec = motor.decidir_honorarios(db, processo_id=processo_id, juiz_nome=proc.juiz,
                                   situacao=situacao, valor_proposto=valor_proposto,
                                   valor_arbitrado=valor_arbitrado)
    acao, nn = dec["acao"], dec["nn"]
    tpath = os.path.join(os.path.dirname(__file__), "..", "templates", "honorarios",
                         TEMPLATE_FILE.get(acao, "proposta.docx"))
    if not os.path.exists(tpath):
        raise FileNotFoundError(tpath)

    hoje = date.today()
    ano2 = hoje.strftime("%y")
    _MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
              "agosto", "setembro", "outubro", "novembro", "dezembro"]
    numero_oficio = f"{int(processo_id):04d}.{ano2}.{_cod_area(proc.especialidade)}.JD.{nn:02d}-{prestador}"
    extras = {
        # DATA só a data (o template já traz "Campo Grande (MS)," antes) — evita duplicar a cidade
        "DATA": f"{hoje.day} de {_MESES[hoje.month]} de {hoje.year}",
        "NUMERO_OFICIO": numero_oficio, "NUMERO_PROCESSO": proc.numero_cnj,
        "OBJETO": objeto or "", "PRESTADOR": str(prestador),
        "VALOR_HONORARIOS": _valor_br(valor_arbitrado), "VALOR": _valor_br(valor_arbitrado),
        "VALOR_MAJORADO": _valor_br(valor_majorado),
        "VALOR_MAJORADO_EXTENSO": _extenso(valor_majorado),
    }
    valores = valores_do_processo(proc, extras=extras)

    from docx import Document
    doc = Document(tpath)
    _preencher_documento(doc, valores)

    pasta = os.path.join(os.environ.get("STORAGE_DIR", "/data/storage"), "oficios",
                         proc.numero_cnj or str(processo_id))
    os.makedirs(pasta, exist_ok=True)
    docx_path = os.path.join(pasta, f"oficio_{acao}_{nn:02d}_{datetime.now():%Y%m%d%H%M%S}.docx")
    doc.save(docx_path)

    of = Oficio(intimacao_id=intimacao_id, processo_id=processo_id, tipo=acao,
                arquivo_docx_path=docx_path, status="gerado")
    db.add(of)
    db.commit()
    db.refresh(of)
    logger.info(f"📄 Ofício {acao} #{of.id} (NN {nn:02d}) gerado: {docx_path}")

    return {"oficio_id": of.id, "acao": acao, "nn": nn, "numero_oficio": numero_oficio,
            "template": TEMPLATE_FILE.get(acao), "docx_path": docx_path,
            "decisao": dec}
