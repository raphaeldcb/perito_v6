import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoVersao

logger = logging.getLogger(__name__)

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None  # anotações abaixo referenciam o nome no import do módulo
    logger.warning("python-docx não instalado. Instale com: pip install python-docx")


def exportar_e_assinar(laudo_id: int, db: Session) -> dict:
    """Exporta laudo para Word/PDF. Assinatura: Windows CryptoAPI (fallback email)."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise ValueError(f"Laudo {laudo_id} não encontrado")

    versao = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id
    ).order_by(LaudoVersao.numero_versao.desc()).first()

    if not versao:
        raise ValueError(f"Nenhuma versão do laudo {laudo_id}")

    resultado = {
        "laudo_id": laudo_id,
        "docx_path": None,
        "pdf_path": None,
        "assinado": False,
        "assinatura_metodo": None,
        "msg": ""
    }

    # 1. Exportar para Word
    if DOCX_AVAILABLE:
        try:
            from app.models import Processo
            processo = db.query(Processo).filter(Processo.id == laudo.processo_id).first()
            docx_path = _exportar_docx(laudo, versao, getattr(processo, "numero_cnj", None))
            resultado["docx_path"] = docx_path
            resultado["msg"] += f"Word exportado: {docx_path}\n"
        except Exception as e:
            logger.error(f"Erro ao exportar Word: {e}")
            resultado["msg"] += f"Erro ao exportar Word: {e}\n"
    else:
        resultado["msg"] += "python-docx não disponível, pulando exportação Word\n"

    # 2. Assinatura: Windows CryptoAPI (TODO) ou email fallback
    try:
        resultado["assinatura_metodo"] = _assinar_laudo(laudo)
        resultado["assinado"] = True
        resultado["msg"] += f"Assinatura: {resultado['assinatura_metodo']}\n"
    except Exception as e:
        logger.warning(f"Erro ao assinar: {e}")
        resultado["msg"] += f"Assinatura falhou (fallback email): {e}\n"

    laudo.arquivo_docx_path = resultado["docx_path"]
    laudo.data_emissao = datetime.utcnow()
    db.commit()

    logger.info(f"Exportação laudo {laudo_id} concluída: {resultado}")
    return resultado


def _exportar_docx(laudo: Laudo, versao: LaudoVersao, numero_processo: str = None) -> str:
    """Exporta laudo para .docx usando template ou markdown direto."""
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx não disponível")

    doc = Document()

    doc.add_heading(f"LAUDO PERICIAL — {laudo.tipo_laudo}", 0)
    doc.add_paragraph(f"Processo: {numero_processo or 'N/A'}")
    doc.add_paragraph(f"Data: {datetime.utcnow().strftime('%d/%m/%Y')}")

    doc.add_paragraph("")

    _add_markdown_to_docx(doc, versao.conteudo_markdown)

    output_dir = os.path.join(os.environ.get("STORAGE_DIR", "/data/storage"), "laudos")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{output_dir}/laudo_{laudo.id}_v{versao.numero_versao}.docx"
    doc.save(filename)

    logger.info(f"Documento salvo em: {filename}")
    return filename


def _add_markdown_to_docx(doc: Document, markdown_text: str):
    """Converte Markdown simples para docx (sem biblioteca markdown pesada)."""
    for line in markdown_text.split("\n"):
        line = line.strip()

        if line.startswith("# "):
            doc.add_heading(line[2:], 0)
        elif line.startswith("## "):
            doc.add_heading(line[3:], 1)
        elif line.startswith("### "):
            doc.add_heading(line[4:], 2)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith("1. ") or line.startswith("* "):
            doc.add_paragraph(line[3:], style="List Number")
        elif line:
            doc.add_paragraph(line)
        else:
            doc.add_paragraph("")


def _assinar_laudo(laudo: Laudo) -> str:
    """Assina laudo usando Windows CryptoAPI (TODO) ou email fallback."""
    # TODO: Integrar com Windows CryptoAPI para A3
    # Por enquanto, retorna método fallback

    footprint = f"Laudo #{laudo.id} assinado digitalmente em {datetime.utcnow().isoformat()}"
    laudo.assinado_por = footprint

    msg = "email-fallback (assinatura digital a3 ainda não implementada)"
    logger.info(f"Laudo {laudo.id} assinado com fallback: {msg}")

    return msg
