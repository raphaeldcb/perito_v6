"""
Laudos DOCX generator — python-docx templating service.

Generates DOCX documents from templates with placeholder replacement.
Supports placeholders: {analise}, {conclusao}, {assinatura}, etc.
"""

import os
import tempfile
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.modules.laudos.models import Laudo, LaudoTemplate, LaudoStatusEnum
from app.modules.laudos.repositories import LaudoRepository, LaudoTemplateRepository
from app.shared.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    ExternalServiceException,
)
from sqlalchemy.orm import Session


class LaudoGeneratorService:
    """DOCX generator for Laudos."""

    # Default output directory for Wave 1 (local /tmp)
    OUTPUT_DIR = "/tmp/laudos"

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.repo = LaudoRepository(db)
        self.template_repo = LaudoTemplateRepository(db)

        # Ensure output directory exists
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def generate_docx(
        self,
        laudo_id: int,
        template_id: Optional[int] = None,
        conteudo_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate DOCX file from template + content.

        Replaces placeholders in template with content values.
        Stores file in /tmp/laudos/{laudo_id}_{timestamp}.docx

        Args:
            laudo_id: Laudo ID
            template_id: Override template (use laudo's template if None)
            conteudo_override: Override content (use laudo's content if None)

        Returns:
            Path to generated DOCX file

        Raises:
            ResourceNotFoundException: If laudo/template not found
            ValidationException: If template empty or content missing
            ExternalServiceException: If generation fails
        """
        # Fetch laudo
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        # Fetch template
        template_to_use = None
        if template_id:
            template_to_use = self.template_repo.get_by_id(template_id)
        elif laudo.template_id:
            template_to_use = self.template_repo.get_by_id(laudo.template_id)
        else:
            # Fallback to first active judicial template
            templates = self.template_repo.list_active()
            template_to_use = next(
                (t for t in templates if t.tipo.value == "judicial"),
                None,
            )

        if not template_to_use:
            raise ResourceNotFoundException(
                detail="Nenhum template encontrado para geração.",
                error_code="TEMPLATE_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        if not template_to_use.conteudo:
            raise ValidationException(
                detail="Template vazio, não pode gerar DOCX.",
                error_code="EMPTY_TEMPLATE",
                context={"template_id": template_to_use.id},
            )

        # Merge content
        content = conteudo_override or laudo.conteudo or {}

        try:
            # Parse template into Document
            doc = self._parse_template_to_document(template_to_use.conteudo)

            # Replace placeholders
            self._replace_placeholders(doc, content)

            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"laudo_{laudo.numero}_{timestamp}.docx"
            filepath = os.path.join(self.OUTPUT_DIR, filename)

            # Save document
            doc.save(filepath)

            # Update laudo with file path
            self.repo.update(laudo_id, arquivo_docx_path=filepath)

            return filepath

        except Exception as e:
            raise ExternalServiceException(
                detail=f"Erro ao gerar DOCX: {str(e)}",
                error_code="DOCX_GENERATION_FAILED",
                context={"laudo_id": laudo_id, "error": str(e)},
            )

    def _parse_template_to_document(self, template_content: str) -> Document:
        """
        Parse template content into a python-docx Document.

        Wave 1: Simple strategy — treat as plain text template.
        Inserts each line as a paragraph.

        Wave 2: Support DOCX templates with embedded fields, using docx-template or similar.

        Args:
            template_content: Template text with placeholders

        Returns:
            python-docx Document object
        """
        doc = Document()

        # Split template into lines and add as paragraphs
        lines = template_content.split("\n")
        for line in lines:
            if line.strip():  # Skip empty lines
                para = doc.add_paragraph(line)
                para.style = "Normal"

        return doc

    def _replace_placeholders(
        self,
        doc: Document,
        content: Dict[str, Any],
    ) -> None:
        """
        Replace placeholders in document with content values.

        Scans all paragraphs and runs, replaces {key} with content[key].

        Placeholders:
        - {analise}: Analysis/reasoning
        - {conclusao}: Conclusion
        - {assinatura}: Signature line
        - {data}: Current date
        - {numero}: Laudo number

        Args:
            doc: python-docx Document
            content: Content dict with replacement values
        """
        # Add standard replacements
        content_with_defaults = {
            "data": datetime.utcnow().strftime("%d/%m/%Y"),
            "numero": content.get("numero", "N/A"),
            **content,
        }

        # Replace in paragraphs
        for para in doc.paragraphs:
            for key, value in content_with_defaults.items():
                placeholder = f"{{{key}}}"
                if placeholder in para.text:
                    para.text = para.text.replace(
                        placeholder,
                        str(value) if value else "",
                    )

        # Replace in tables (if any)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for key, value in content_with_defaults.items():
                            placeholder = f"{{{key}}}"
                            if placeholder in para.text:
                                para.text = para.text.replace(
                                    placeholder,
                                    str(value) if value else "",
                                )

    def update_docx_content(
        self,
        laudo_id: int,
        conteudo: Dict[str, Any],
    ) -> str:
        """
        Regenerate DOCX with new content.

        Useful when Laudo content is updated and needs re-rendering.

        Args:
            laudo_id: Laudo ID
            conteudo: New content dict

        Returns:
            Path to regenerated DOCX
        """
        return self.generate_docx(
            laudo_id,
            conteudo_override=conteudo,
        )

    def seed_default_templates(self) -> None:
        """
        Seed default Laudo templates for Wave 1.

        Called during bootstrap or migrations.
        Idempotent — only creates if não exist.
        """
        from app.modules.laudos.models import LaudoTipoEnum

        templates = [
            {
                "nome": "Modelo Padrão Judicial",
                "tipo": LaudoTipoEnum.JUDICIAL,
                "descricao": "Template padrão para perícias judiciais",
                "conteudo": self._default_judicial_template(),
                "ativo": True,
            },
            {
                "nome": "Modelo Padrão Extrajudicial",
                "tipo": LaudoTipoEnum.EXTRAJUDICIAL,
                "descricao": "Template padrão para perícias extrajudiciais",
                "conteudo": self._default_extrajudicial_template(),
                "ativo": True,
            },
        ]

        for tpl in templates:
            existing = self.template_repo.get_by_nome(tpl["nome"])
            if not existing:
                self.template_repo.create(**tpl)

    def _default_judicial_template(self) -> str:
        """Default judicial laudo template."""
        return """
LAUDO PERICIAL

Número: {numero}
Data: {data}

ANÁLISE

{analise}

CONCLUSÃO

{conclusao}

___________________
{assinatura}
"""

    def _default_extrajudicial_template(self) -> str:
        """Default extrajudicial laudo template."""
        return """
LAUDO TÉCNICO EXTRAJUDICIAL

Número: {numero}
Data: {data}

INTRODUÇÃO

Perícia realizada conforme solicitado.

ANÁLISE

{analise}

CONCLUSÃO

{conclusao}

Responsável Técnico:
{assinatura}
"""
