"""
Conversor DOCX → PDF usando LibreOffice headless.
Task 5: Converter DOCX → PDF (LibreOffice Headless)
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ForensicDocxToPdf:
    """Converte DOCX em PDF via LibreOffice."""

    # Supported LibreOffice paths (VPS Linux and Mac)
    LIBREOFFICE_PATHS = [
        "/usr/bin/libreoffice",  # Linux (VPS)
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
    ]
    TIMEOUT_SECONDS = 30

    def __init__(self):
        """Initialize and find LibreOffice binary."""
        self.libreoffice_path = self._find_libreoffice()
        if not self.libreoffice_path:
            raise FileNotFoundError(
                f"LibreOffice not found. Tried paths: {self.LIBREOFFICE_PATHS}. "
                f"Linux: apt-get install -y libreoffice-writer. "
                f"macOS: brew install libreoffice"
            )

    def _find_libreoffice(self) -> Optional[str]:
        """Find LibreOffice binary in standard locations."""
        for path in self.LIBREOFFICE_PATHS:
            if Path(path).exists():
                return path
        return None

    def convert(self, docx_bytes: bytes) -> bytes:
        """
        Converte DOCX (bytes) em PDF (bytes).

        Args:
            docx_bytes: Conteúdo DOCX

        Returns:
            bytes: Conteúdo PDF

        Raises:
            FileNotFoundError: Se LibreOffice não estiver instalado
            Exception: Se ocorrer erro na conversão
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Salvar DOCX temporário
            docx_path = tmpdir / "input.docx"
            docx_path.write_bytes(docx_bytes)

            # Converter via LibreOffice
            pdf_path = tmpdir / "input.pdf"

            try:
                # Run LibreOffice in headless mode
                result = subprocess.run(
                    [
                        self.libreoffice_path,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(tmpdir),
                        str(docx_path),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=self.TIMEOUT_SECONDS,
                    text=True,
                )

                # Ler PDF
                if not pdf_path.exists():
                    error_msg = (
                        f"PDF file not generated. "
                        f"stdout: {result.stdout}, "
                        f"stderr: {result.stderr}"
                    )
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg)

                pdf_content = pdf_path.read_bytes()
                logger.info(
                    f"DOCX→PDF conversion successful: {len(docx_bytes)} bytes → "
                    f"{len(pdf_content)} bytes"
                )

                return pdf_content

            except subprocess.TimeoutExpired as e:
                error_msg = (
                    f"LibreOffice timeout after {self.TIMEOUT_SECONDS}s. "
                    f"DOCX too complex or system overloaded."
                )
                logger.error(error_msg)
                raise Exception(error_msg) from e

            except subprocess.CalledProcessError as e:
                error_msg = f"LibreOffice conversion failed: {e.stderr}"
                logger.error(error_msg)
                raise Exception(error_msg) from e

            except Exception as e:
                error_msg = f"Unexpected error during DOCX→PDF conversion: {str(e)}"
                logger.error(error_msg)
                raise
