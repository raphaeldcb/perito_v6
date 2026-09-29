"""
Laudos PDF export service — DOCX to PDF conversion.

Uses LibreOffice CLI or Pandoc for format conversion.
Wave 1: LibreOffice headless via subprocess. Wave 2: Async with celery.
"""

import os
import subprocess
import tempfile
from typing import Optional
from pathlib import Path
from datetime import datetime

from app.modules.laudos.repositories import LaudoRepository
from app.shared.exceptions import (
    ResourceNotFoundException,
    ExternalServiceException,
    ValidationException,
)
from sqlalchemy.orm import Session


class LaudoPdfService:
    """PDF generation and export service."""

    # Default output directory for Wave 1 (local /tmp)
    OUTPUT_DIR = "/tmp/laudos"
    PDF_TIMEOUT = 60  # 60 seconds timeout for conversion

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.repo = LaudoRepository(db)

        # Ensure output directory exists
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def docx_to_pdf(self, laudo_id: int, docx_path: str) -> str:
        """
        Convert DOCX to PDF using LibreOffice.

        Saves PDF to /tmp/laudos/{laudo_id}_{timestamp}.pdf

        Args:
            laudo_id: Laudo ID (for context/logging)
            docx_path: Full path to DOCX file

        Returns:
            Path to generated PDF file

        Raises:
            ValidationException: If DOCX not found
            ExternalServiceException: If conversion fails or LibreOffice unavailable
        """
        # Validate DOCX exists
        if not os.path.exists(docx_path):
            raise ValidationException(
                detail=f"Arquivo DOCX não encontrado: {docx_path}",
                error_code="DOCX_NOT_FOUND",
                context={"docx_path": docx_path},
            )

        try:
            # Generate PDF output path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"laudo_{laudo_id}_{timestamp}.pdf"
            pdf_path = os.path.join(self.OUTPUT_DIR, pdf_filename)

            # Try LibreOffice first (preferred)
            if self._has_libreoffice():
                self._convert_with_libreoffice(docx_path, pdf_path)
            elif self._has_pandoc():
                self._convert_with_pandoc(docx_path, pdf_path)
            else:
                raise ExternalServiceException(
                    detail="LibreOffice ou Pandoc não encontrado no sistema.",
                    error_code="NO_PDF_CONVERTER",
                    context={},
                )

            # Verify PDF was created
            if not os.path.exists(pdf_path):
                raise ExternalServiceException(
                    detail="PDF não foi gerado corretamente.",
                    error_code="PDF_GENERATION_FAILED",
                    context={"docx_path": docx_path},
                )

            # Update laudo with PDF path
            self.repo.update(laudo_id, arquivo_pdf_path=pdf_path)

            return pdf_path

        except ExternalServiceException:
            raise
        except Exception as e:
            raise ExternalServiceException(
                detail=f"Erro ao converter DOCX para PDF: {str(e)}",
                error_code="PDF_CONVERSION_ERROR",
                context={"laudo_id": laudo_id, "docx_path": docx_path, "error": str(e)},
            )

    def generate_pdf_from_laudo(self, laudo_id: int) -> str:
        """
        Generate PDF from Laudo (requires DOCX to exist first).

        Convenience method that:
        1. Checks laudo exists and has DOCX
        2. Converts DOCX to PDF
        3. Returns PDF path

        Args:
            laudo_id: Laudo ID

        Returns:
            Path to PDF file

        Raises:
            ResourceNotFoundException: If laudo not found
            ValidationException: If DOCX not generated yet
        """
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        if not laudo.arquivo_docx_path:
            raise ValidationException(
                detail=f"Laudo {laudo_id} não tem DOCX gerado. Gere antes de converter para PDF.",
                error_code="DOCX_NOT_GENERATED",
                context={"laudo_id": laudo_id},
            )

        return self.docx_to_pdf(laudo_id, laudo.arquivo_docx_path)

    def _has_libreoffice(self) -> bool:
        """Check if LibreOffice is available."""
        try:
            subprocess.run(
                ["libreoffice", "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _has_pandoc(self) -> bool:
        """Check if Pandoc is available."""
        try:
            subprocess.run(
                ["pandoc", "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _convert_with_libreoffice(self, docx_path: str, output_pdf_path: str) -> None:
        """
        Convert DOCX to PDF using LibreOffice headless.

        Command: libreoffice --headless --convert-to pdf {docx_path} --outdir {output_dir}

        Args:
            docx_path: Full path to DOCX
            output_pdf_path: Full path for output PDF

        Raises:
            ExternalServiceException: If conversion fails
        """
        output_dir = os.path.dirname(output_pdf_path)

        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            docx_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.PDF_TIMEOUT,
            )

            if result.returncode != 0:
                raise ExternalServiceException(
                    detail=f"LibreOffice conversion failed: {result.stderr}",
                    error_code="LIBREOFFICE_CONVERSION_ERROR",
                    context={
                        "docx_path": docx_path,
                        "stderr": result.stderr,
                        "stdout": result.stdout,
                    },
                )

        except subprocess.TimeoutExpired:
            raise ExternalServiceException(
                detail=f"LibreOffice conversion timed out after {self.PDF_TIMEOUT}s",
                error_code="LIBREOFFICE_TIMEOUT",
                context={"docx_path": docx_path},
            )

    def _convert_with_pandoc(self, docx_path: str, output_pdf_path: str) -> None:
        """
        Convert DOCX to PDF using Pandoc.

        Command: pandoc {docx_path} -o {pdf_path}

        Args:
            docx_path: Full path to DOCX
            output_pdf_path: Full path for output PDF

        Raises:
            ExternalServiceException: If conversion fails
        """
        cmd = [
            "pandoc",
            docx_path,
            "-o", output_pdf_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.PDF_TIMEOUT,
            )

            if result.returncode != 0:
                raise ExternalServiceException(
                    detail=f"Pandoc conversion failed: {result.stderr}",
                    error_code="PANDOC_CONVERSION_ERROR",
                    context={
                        "docx_path": docx_path,
                        "stderr": result.stderr,
                        "stdout": result.stdout,
                    },
                )

        except subprocess.TimeoutExpired:
            raise ExternalServiceException(
                detail=f"Pandoc conversion timed out after {self.PDF_TIMEOUT}s",
                error_code="PANDOC_TIMEOUT",
                context={"docx_path": docx_path},
            )

    def cleanup_old_files(self, laudo_id: int) -> None:
        """
        Clean up old DOCX/PDF files for a laudo (keep latest).

        Wave 1: Manual call. Wave 2: Automated via task scheduler.

        Args:
            laudo_id: Laudo ID
        """
        # List all files for this laudo in output directory
        pattern = f"laudo_{laudo_id}_*.docx"
        pattern_pdf = f"laudo_{laudo_id}_*.pdf"

        # Find and delete old versions (keep latest 2)
        import glob

        docx_files = sorted(
            glob.glob(os.path.join(self.OUTPUT_DIR, pattern)),
            key=os.path.getmtime,
            reverse=True,
        )
        pdf_files = sorted(
            glob.glob(os.path.join(self.OUTPUT_DIR, pattern_pdf)),
            key=os.path.getmtime,
            reverse=True,
        )

        # Keep latest 2, delete older
        for old_file in docx_files[2:]:
            try:
                os.remove(old_file)
            except OSError:
                pass

        for old_file in pdf_files[2:]:
            try:
                os.remove(old_file)
            except OSError:
                pass
