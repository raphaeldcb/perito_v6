"""Gera o comprovante de pagamento (PDF) de um lançamento conciliado e o
anexa ao portal do coletador, com nome de arquivo padronizado.

Nome: comprovante_<competencia>_<nome-sanitizado>.pdf
"""
import os
import re
import unicodedata
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Coletador, DocumentoColetador, Empresa, LancamentoBancario


def _sanitizar(nome: str) -> str:
    n = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    n = re.sub(r"[^A-Za-z0-9]+", "-", n).strip("-")
    return n[:60] or "coletador"


def _ascii(txt: str) -> str:
    # a fonte core Helvetica não tem glifos unicode — normaliza para latin-1
    return unicodedata.normalize("NFKD", str(txt or "")).encode("latin-1", "ignore").decode("latin-1")


def _valor_br(v) -> str:
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _gerar_pdf(caminho: str, empresa: Empresa, coletador: Coletador,
               lanc: LancamentoBancario, competencia: str) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    largura = pdf.w - pdf.l_margin - pdf.r_margin  # área útil

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(largura, 12, _ascii("COMPROVANTE DE PAGAMENTO"), align="C")
    pdf.ln(4)

    razao = empresa.razao_social if empresa else "IPC MS PESQUISA LTDA"
    cnpj = empresa.cnpj if empresa else "14.424.142/0001-90"
    banco = (empresa.banco if empresa else "") or (lanc.extrato.banco if lanc.extrato else "")

    linhas = [
        ("Pagador", f"{razao}  |  CNPJ {cnpj}"),
        ("Favorecido", coletador.nome_completo),
        ("CPF", coletador.cpf),
        ("Chave PIX", coletador.pix or "-"),
        ("Competencia", competencia),
        ("Data do pagamento", lanc.data.strftime("%d/%m/%Y") if lanc.data else "-"),
        ("Valor", _valor_br(lanc.valor)),
        ("Banco", banco or "-"),
        ("Historico", (lanc.descricao or "")[:120]),
    ]
    for rotulo, valor in linhas:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(40, 8, _ascii(rotulo + ":"), align="L",
                       new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(largura - 40, 8, _ascii(valor), align="L",
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(largura, 6, _ascii(
        "Documento gerado automaticamente pela conciliacao bancaria do sistema IPC MS "
        f"em {datetime.now().strftime('%d/%m/%Y %H:%M')}. Referente a credito identificado "
        "no extrato bancario da empresa."))
    pdf.output(caminho)


def gerar_comprovante_para_lancamento(db: Session, lanc: LancamentoBancario) -> DocumentoColetador | None:
    """Cria (ou reaproveita) o comprovante PDF de um lançamento conciliado a um
    coletador. Idempotente: um lançamento tem no máximo um comprovante."""
    if not lanc.coletador_id:
        return None

    coletador = db.query(Coletador).filter(Coletador.id == lanc.coletador_id).first()
    if not coletador:
        return None
    # Sócios/prestadores (ex: o próprio Bruno) recebem por outras formas e são
    # tratados manualmente — não geram comprovante de conveniado automático.
    if coletador.is_prestador:
        return None

    competencia = lanc.extrato.competencia if lanc.extrato else datetime.now().strftime("%Y-%m")
    empresa = None
    if coletador.empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == coletador.empresa_id).first()

    base = os.path.join(settings.storage_dir, "coletadores", str(coletador.id))
    os.makedirs(base, exist_ok=True)
    # Padrão SCPG: CODIGO.ANO.MES.pdf (ex: 297.26.01.pdf). Competência = "YYYY-MM".
    try:
        ano, mes = competencia.split("-")[:2]
        ref_scpg = f"{coletador.codigo_scpg:03d}.{ano[2:]}.{mes}" if coletador.codigo_scpg else None
    except (ValueError, AttributeError):
        ref_scpg = None
    if ref_scpg:
        nome_arq = f"{ref_scpg}.pdf"
    else:
        nome_arq = f"comprovante_{competencia}_{_sanitizar(coletador.nome_completo)}.pdf"
    caminho = os.path.join(base, nome_arq)

    try:
        _gerar_pdf(caminho, empresa, coletador, lanc, competencia)
    except Exception:
        caminho = None  # se a geração do PDF falhar, ainda registra o comprovante estruturado

    # já existe comprovante para este lançamento?
    doc = None
    if lanc.comprovante_id:
        doc = db.query(DocumentoColetador).filter(DocumentoColetador.id == lanc.comprovante_id).first()
    if not doc:
        doc = DocumentoColetador(coletador_id=coletador.id, tipo="comprovante")
        db.add(doc)
        db.flush()
        lanc.comprovante_id = doc.id

    doc.coletador_id = coletador.id
    doc.titulo = f"Comprovante {competencia}"
    doc.referencia = competencia
    doc.valor = lanc.valor
    doc.arquivo_path = caminho
    doc.dados_formulario = {
        "favorecido": lanc.favorecido,
        "data": lanc.data.isoformat() if lanc.data else None,
        "banco": (lanc.extrato.banco if lanc.extrato else None),
        "origem": "conciliacao_extrato",
    }
    return doc
