"""Job: Extrai texto de PDF ofício via pdfminer"""
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
import logging

logger = logging.getLogger(__name__)

def extrair_texto_pdf(pdf_path: str, paginas: int = None) -> dict:
    """
    Extrai texto do PDF com qualidade >= 95%
    
    Args:
        pdf_path: caminho local do PDF
        paginas: limitar a N primeiras páginas (None = tudo)
    
    Returns:
        {
            "texto": "...",
            "qualidade": 0.98,
            "paginas": 5,
            "erro": None
        }
    """
    try:
        # Extrair com layout
        laparams = LAParams(word_margin=0.1)
        texto = extract_text(pdf_path, laparams=laparams, maxpages=paginas or 0)
        
        # Medir qualidade (% caracteres válidos)
        total_chars = len(texto)
        valid_chars = sum(1 for c in texto if c.isprintable() or c.isspace())
        qualidade = valid_chars / total_chars if total_chars > 0 else 0
        
        # Contar páginas
        paginas_count = len(texto.split('\x0c'))
        
        return {
            "texto": texto[:50000],  # Limitar output
            "qualidade": qualidade,
            "paginas": paginas_count,
            "erro": None
        }
    except Exception as e:
        logger.error(f"Erro extração PDF {pdf_path}: {e}")
        return {
            "texto": None,
            "qualidade": 0,
            "paginas": 0,
            "erro": str(e)
        }
