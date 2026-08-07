"""
Routes for forensic analysis laudo download.

Provides endpoint to download DOCX/PDF laudos from OneDrive.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.services.database import SessionLocal
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forensic", tags=["forensic"])


class OneDriveClient:
    """Client for downloading files from OneDrive."""

    def __init__(self):
        pass

    def download_file(self, file_url: str) -> bytes:
        """
        Download file from OneDrive URL.

        Args:
            file_url: OneDrive file URL

        Returns:
            File bytes

        Raises:
            Exception: If download fails
        """
        import requests

        try:
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise Exception(f"Falha ao baixar arquivo do OneDrive: {e}")


@router.get("/{analysis_id}/laudo-download")
async def download_forensic_laudo(
    analysis_id: str,
    format: str = "docx",
):
    """
    Download forensic laudo in DOCX or PDF format from OneDrive.

    **Endpoint**: `GET /api/v1/forensic/{analysis_id}/laudo-download`

    **Query Parameters**:
    - `format` (string, default: "docx"): File format - "docx" or "pdf"

    **Returns**:
    - 200: File bytes with proper Content-Type and Content-Disposition headers
    - 404: If analysis not found or laudo not generated
    - 500: If download fails

    **Example**:
    ```bash
    curl -O "http://localhost:8000/api/v1/forensic/abc123/laudo-download?format=pdf"
    ```
    """
    db = SessionLocal()
    try:
        # Validate format parameter
        if format.lower() not in ["docx", "pdf"]:
            raise HTTPException(
                status_code=400,
                detail="Format deve ser 'docx' ou 'pdf'",
            )

        # Import model here to avoid circular imports
        from app.models.forensic import ForensicAnalysis

        # Query database for analysis by ID
        analysis = db.query(ForensicAnalysis).filter(
            ForensicAnalysis.id == int(analysis_id)
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Análise forense não encontrada",
            )

        # Determine which URL to use based on format
        format_lower = format.lower()
        if format_lower == "docx":
            laudo_url = analysis.laudo_docx_url
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        else:  # pdf
            laudo_url = analysis.laudo_pdf_url
            content_type = "application/pdf"
            ext = "pdf"

        # Check if laudo URL exists
        if not laudo_url:
            raise HTTPException(
                status_code=404,
                detail=f"Laudo em formato {format_lower.upper()} não foi gerado para esta análise",
            )

        # Download file from OneDrive
        client = OneDriveClient()
        file_bytes = client.download_file(laudo_url)

        # Generate filename with analysis ID
        codigo_laudo = (
            analysis.resultado_json.get("codigo_laudo", f"L{analysis.id:08d}")
            if analysis.resultado_json
            else f"L{analysis.id:08d}"
        )
        filename = f"Laudo_{codigo_laudo[:8]}.{ext}"

        # Return file as download with proper headers
        return StreamingResponse(
            iter([file_bytes]),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )

    except HTTPException:
        raise
    except ValueError:
        # Invalid analysis_id format (not an integer)
        raise HTTPException(
            status_code=404,
            detail="Análise forense não encontrada",
        )
    except Exception as e:
        logger.error(f"Erro ao baixar laudo: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro ao baixar laudo",
        )
    finally:
        db.close()
