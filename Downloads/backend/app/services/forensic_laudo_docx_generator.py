"""
Gerador de Laudo Forense em DOCX.
Preenche template DOCX com dados de análise forense.
"""
from pathlib import Path
from io import BytesIO
from docx import Document
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ForensicLaudoDocxGenerator:
    """Gera DOCX de laudo forense preenchido com dados reais."""

    TEMPLATE_PATH = Path("/var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx")

    def __init__(self, template_path: Optional[Path] = None):
        """
        Initialize generator with template path.

        Args:
            template_path: Optional path to template. Uses default VPS path if None.

        Raises:
            FileNotFoundError: If template does not exist.
        """
        self.template_path = template_path or self.TEMPLATE_PATH

        if not self.template_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {self.template_path}")

    def generate(self, analysis_data: Dict[str, str]) -> bytes:
        """
        Gera DOCX preenchido com dados de análise.

        Args:
            analysis_data: Dict com chaves em minúsculas (codigo_laudo, contratante, etc.)

        Returns:
            bytes: DOCX gerado (salvo em memória)
        """
        # Carregar template
        doc = Document(self.template_path)

        # Converter keys para {{MAIUSCULA}} e preparar mapeamento
        replacements = self._prepare_replacements(analysis_data)

        # Substituir em parágrafos
        for para in doc.paragraphs:
            for replacement, value in replacements.items():
                if replacement in para.text:
                    self._replace_in_paragraph(para, replacement, value)

        # Substituir em tabelas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for replacement, value in replacements.items():
                            if replacement in para.text:
                                self._replace_in_paragraph(para, replacement, value)

        # Salvar em memória
        output = BytesIO()
        doc.save(output)
        output.seek(0)

        return output.getvalue()

    def _prepare_replacements(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Converte chaves minúsculas em {{MAIUSCULA}}.

        Args:
            data: Dict com chaves em minúsculas

        Returns:
            Dict mapeado com placeholders {{MAIUSCULA}} como chaves
        """
        replacements = {}
        for key, value in data.items():
            placeholder = '{{' + key.upper() + '}}'
            # Convert value to string, handle None gracefully
            replacements[placeholder] = str(value) if value is not None else "[NÃO PREENCHIDO]"
        return replacements

    def _replace_in_paragraph(self, para, old_text: str, new_text: str) -> None:
        """
        Substitui texto em parágrafo preservando formatação.

        Uses a simple strategy: clear all runs and add new run with replaced text.

        Args:
            para: Paragraph object from python-docx
            old_text: Text to find (e.g., {{CODIGO_LAUDO}})
            new_text: Text to replace with
        """
        if old_text not in para.text:
            return

        # Build new text by replacing all occurrences
        full_text = para.text
        new_full_text = full_text.replace(old_text, new_text)

        # Clear existing runs (preserves paragraph but removes formatting)
        for run in para.runs:
            r = run._element
            r.getparent().remove(r)

        # Add new run with replaced text
        para.add_run(new_full_text)
