"""
Gerador automático de ofícios — integra dados estruturados de intimação
com templates Word, exporta para DOCX e PDF.
"""
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def gerar_oficio(intimacao, tipo: str = "requerimento") -> dict:
    """
    Gera ofício a partir de dados estruturados de intimação.

    Args:
        intimacao: Objeto Intimacao com dados_estruturados preenchido
        tipo: requerimento, manifestacao, resposta_quesito

    Returns:
        dict com caminho do oficio_docx_path e status
    """
    from app.services.oficio import valores_do_processo
    from docx import Document
    import tempfile

    if not intimacao.dados_estruturados:
        raise ValueError(f"Intimação {intimacao.id} sem dados_estruturados")

    dados = intimacao.dados_estruturados
    processo = intimacao.processo

    # Monta valores do processo (campo →valor)
    valores = valores_do_processo(
        processo,
        extras={
            "JUIZ": dados.get("juiz", ""),
            "VARA": dados.get("vara", ""),
            "PRAZO_DIAS": str(dados.get("prazo_dias", "")),
            "RESUMO_INTIMACAO": dados.get("resumo", ""),
        },
    )

    # Seleciona template
    template_path = _selecionar_template(tipo)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template não encontrado: {template_path}")

    # Abre template e preenche campos
    doc = Document(template_path)
    _preencher_documento(doc, valores)

    # Salva em storage
    pasta = os.path.join(
        os.environ.get("STORAGE_DIR", "/data/storage"),
        "oficios",
        f"{processo.numero_cnj}",
    )
    os.makedirs(pasta, exist_ok=True)

    docx_path = os.path.join(pasta, f"oficio_{tipo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx")
    doc.save(docx_path)

    logger.info(f"📄 Ofício gerado: {docx_path}")

    return {
        "oficio_docx_path": docx_path,
        "tipo": tipo,
        "status": "gerado",
    }


def _selecionar_template(tipo: str) -> str:
    """Retorna caminho do template baseado no tipo de ofício."""
    templates = {
        "requerimento": "oficio_requerimento.docx",
        "manifestacao": "oficio_manifestacao.docx",
        "resposta_quesito": "oficio_resposta_quesito.docx",
    }
    template_nome = templates.get(tipo, "oficio_padrao.docx")
    return os.path.join(os.path.dirname(__file__), "..", "templates", template_nome)


def _preencher_documento(doc, valores: dict) -> None:
    """Substitui {{CAMPO}} por valores no documento."""
    # Parágrafos
    for paragrafo in doc.paragraphs:
        for campo, valor in valores.items():
            placeholder = f"{{{{{campo}}}}}"
            if placeholder in paragrafo.text:
                paragrafo.text = paragrafo.text.replace(placeholder, str(valor or ""))

    # Tabelas
    for tabela in doc.tables:
        for linha in tabela.rows:
            for celula in linha.cells:
                for paragrafo in celula.paragraphs:
                    for campo, valor in valores.items():
                        placeholder = f"{{{{{campo}}}}}"
                        if placeholder in paragrafo.text:
                            paragrafo.text = paragrafo.text.replace(placeholder, str(valor or ""))
