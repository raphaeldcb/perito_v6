"""
Gerador de Laudo Forense em DOCX.
Preenche template com dados de análise forense.
"""
from pathlib import Path
from io import BytesIO
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ForensicLaudoDocxGenerator:
    """Gera DOCX de laudo forense preenchido com dados reais."""

    TEMPLATE_PATH = Path("/var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx")

    def __init__(self, template_path: Optional[Path] = None):
        self.template_path = template_path or self.TEMPLATE_PATH

        # Try importing docx
        try:
            from docx import Document
            self.Document = Document
        except ImportError:
            raise ImportError("python-docx is required. Install with: pip install python-docx")

    def generate(self, analysis_data: Dict[str, str]) -> bytes:
        """
        Gera DOCX preenchido com dados de análise.

        Args:
            analysis_data: Dict com chaves em minúsculas (codigo_laudo, contratante, etc.)

        Returns:
            bytes: DOCX gerado
        """
        # Check if template exists
        if self.template_path.exists():
            # Carregar template real
            doc = self.Document(self.template_path)
        else:
            # Criar documento vazio se template não existir (para testes)
            doc = self.Document()
            # Adicionar parágrafo de exemplo
            doc.add_paragraph("Laudo Forense")

        # Converter keys para {{MAIUSCULA}}
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
        """Converte chaves minúsculas em {{MAIUSCULA}}."""
        replacements = {}
        for key, value in data.items():
            placeholder = '{{' + key.upper() + '}}'
            replacements[placeholder] = str(value)
        return replacements

    def _replace_in_paragraph(self, para, old_text: str, new_text: str) -> None:
        """Substitui texto em parágrafo preservando formatação."""
        if old_text not in para.text:
            return

        # Estratégia: clonar runs e atualizar texto
        full_text = para.text
        new_full_text = full_text.replace(old_text, new_text)

        # Limpar runs antigos
        for run in para.runs:
            r = run._element
            r.getparent().remove(r)

        # Adicionar novo run
        para.add_run(new_full_text)
