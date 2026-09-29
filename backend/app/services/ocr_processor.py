"""
OCR para PDFs — tenta pypdf primeiro, fallback para Tesseract se imagem.
Salva texto extraído em arquivo .txt para rastreabilidade.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def extrair_texto_com_ocr(pdf_path: str) -> str:
    """
    Extrai texto de PDF. Prioridade:
    1. pypdf (rápido, zero deps extras)
    2. Tesseract OCR se pypdf falhar ou retornar < 100 chars (imagem)
    3. Erro se ambas falharem

    Retorna: texto extraído (mín 50 chars) ou levanta ValueError
    Salva em: {pdf_dir}/texto.txt
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    pdf_dir = os.path.dirname(pdf_path)
    texto_path = os.path.join(pdf_dir, "texto.txt")

    # Tentativa 1: pypdf (nativo)
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        texto = "\n".join(page.extract_text() or "" for page in reader.pages[:30])

        if len(texto.strip()) >= 50:
            _salvar_texto(texto, texto_path)
            logger.info(f"✅ Texto extraído com pypdf: {len(texto)} chars")
            return texto
        else:
            logger.debug(f"pypdf retornou pouco texto ({len(texto)} chars), tentando OCR...")
    except Exception as e:
        logger.debug(f"pypdf falhou: {e}, tentando OCR...")

    # Tentativa 2: Tesseract OCR
    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(pdf_path, last_page=10)
        texto = "\n---\n".join(
            pytesseract.image_to_string(img, lang="por", config="--psm 6 --oem 1")
            for img in images
        )

        if len(texto.strip()) >= 50:
            _salvar_texto(texto, texto_path)
            logger.info(f"✅ Texto extraído com Tesseract OCR: {len(texto)} chars")
            return texto
        else:
            raise ValueError(f"Tesseract retornou pouco texto: {len(texto)} chars")

    except ImportError:
        raise ImportError(
            "Tesseract não instalado. Execute:\n"
            "  VPS: apt-get install tesseract-ocr\n"
            "  Mac: brew install tesseract\n"
            "  Pip: pip install pytesseract pdf2image"
        )
    except Exception as e:
        raise RuntimeError(f"OCR falhou completamente: {e}")


def _salvar_texto(texto: str, caminho: str) -> None:
    """Salva texto extraído em arquivo."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    logger.debug(f"📄 Texto salvo em {caminho}")
