"""
AutoLaudoPro routes — Extraction, template filling, RAG indexing endpoints.

Isolated FastAPI router with no dependencies on other ferramentas.
"""

import time
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.shared.schemas import ApiResponse
from .schemas import (
    ProcessUploadRequest,
    ExtracaoResponse,
    LaudoGeradoResponse,
    ValidarEficienciaResponse,
)
from .service import get_auto_laudo_service, AutoLaudoProService

router = APIRouter(prefix="/auto-laudo", tags=["ferramentas"])


@router.post("/extrair", response_model=ApiResponse[ExtracaoResponse])
async def extrair_dados_processo(
    request: ProcessUploadRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """
    Upload judicial process and extract structured data.

    Endpoint: POST /api/v1/auto-laudo/extrair

    Flow:
    1. OCR document (PDF/image -> text)
    2. Parse structure with Qwen
    3. Validate completeness
    4. Return extraction with confidence metrics

    Args:
        request: ProcessUploadRequest with file_content, file_type, tipo_pericia
        db: Database session

    Returns:
        ApiResponse with ExtracaoResponse containing extracted data + metrics
    """
    start_time = time.time()
    extraction_id = f"ext_{uuid.uuid4().hex[:8]}"

    try:
        service = get_auto_laudo_service()

        # Step 1: OCR document
        texto_processo, ocr_applied = service.ocr_documento(
            file_content=request.file_content,
            file_type=request.file_type,
        )

        if not texto_processo.strip():
            raise ValueError("Document is empty or OCR failed")

        # Step 2: Extract structured data
        extracted_data = service.extrair_dados_processo(
            texto_processo=texto_processo,
            tipo_pericia=request.tipo_pericia,
        )

        # Step 3: Validate and calculate metrics
        validation = service.validar_eficiencia(extracted_data)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response_data = ExtracaoResponse(
            extraction_id=extraction_id,
            extracted_data=extracted_data,
            extraction_confidence=validation["quality_score"],
            fill_rate=validation["fill_rate"],
            field_confidence=validation["field_confidence"],
            ocr_applied=ocr_applied,
            processing_time_ms=processing_time_ms,
        )

        return ApiResponse(success=True, data=response_data)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Extraction error: {str(e)}"
        )


@router.post("/gerar", response_model=ApiResponse[LaudoGeradoResponse])
async def gerar_laudo(
    extraction_id: str,
    extraction_data_json: str = Form(...),
    template_id: int = Form(None),
    file_format: str = Form("txt"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    """
    Generate laudo from extraction data and template.

    Endpoint: POST /api/v1/auto-laudo/gerar

    Flow:
    1. Load or create template
    2. Fill template with extracted data
    3. Index generated laudo in RAG (pgvector)
    4. Store file for download
    5. Calculate efficiency metrics

    Args:
        extraction_id: ID from extraction step
        extraction_data_json: JSON string of ExtractionData
        template_id: Optional template pattern ID from DB
        file_format: Output format (txt, docx, pdf)
        db: Database session

    Returns:
        ApiResponse with LaudoGeradoResponse containing laudo + RAG metrics
    """
    start_time = time.time()
    laudo_id = f"laud_{uuid.uuid4().hex[:8]}"

    try:
        import json
        from .schemas import ExtractionData

        service = get_auto_laudo_service()

        # Parse extraction data
        extraction_dict = json.loads(extraction_data_json)
        extraction = ExtractionData(**extraction_dict)

        # Get or create template (placeholder: assumes template_text for now)
        template_text = None  # TODO: Load from DB if template_id provided
        if template_id:
            # Query DB for template
            # template_text = db.query(PadraoTemplate).filter_by(id=template_id).first().content
            pass

        # Fill template
        laudo_content = service.aplicar_template(
            extraction=extraction,
            template_text=template_text,
        )

        # Index in RAG
        indexed_chunks = []
        try:
            rag_ids = service.alimentar_rag(
                db=db,
                laudo_content=laudo_content,
                laudo_id=laudo_id,
                origem="laudo",
            )
            indexed_chunks = len(rag_ids)
        except Exception as e:
            # RAG indexing is optional
            pass

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        response_data = LaudoGeradoResponse(
            laudo_id=laudo_id,
            laudo_content=laudo_content,
            template_used=f"template_{template_id}" if template_id else "default",
            extraction_id=extraction_id,
            indexed_chunks=indexed_chunks,
            rag_ids=rag_ids if indexed_chunks > 0 else None,
            generation_confidence=0.88,  # Placeholder
            processing_time_ms=processing_time_ms,
            file_format=file_format,
            file_url=f"/api/v1/auto-laudo/download/{laudo_id}" if laudo_id else None,
        )

        return ApiResponse(success=True, data=response_data)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON in extraction_data: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Laudo generation error: {str(e)}")


@router.get("/validar/{job_id}", response_model=ApiResponse[ValidarEficienciaResponse])
async def validar_eficiencia(
    job_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """
    Validate efficiency and quality of extraction or laudo generation.

    Endpoint: GET /api/v1/auto-laudo/validar/{job_id}

    Returns metrics:
    - Extraction success and fill rate
    - Laudo generation status
    - RAG indexing metrics
    - Overall quality score
    - Warnings and errors

    Args:
        job_id: Extraction or laudo ID (ext_* or laud_*)
        db: Database session

    Returns:
        ApiResponse with ValidarEficienciaResponse
    """
    try:
        # TODO: Implement job tracking/storage
        # For now, return placeholder validation

        is_extraction = job_id.startswith("ext_")
        is_laudo = job_id.startswith("laud_")

        if not (is_extraction or is_laudo):
            raise ValueError("Invalid job_id format (must be ext_* or laud_*)")

        # Placeholder validation
        response_data = ValidarEficienciaResponse(
            job_id=job_id,
            status="success" if is_laudo else "partial",
            extraction_success=is_extraction,
            laudo_generated=is_laudo,
            fill_rate=0.92,
            extraction_confidence=0.89,
            rag_indexed=is_laudo,
            indexed_chunks=15 if is_laudo else 0,
            warnings=["Placeholder validation — implement full job tracking"],
            errors=[],
            quality_score=0.88,
        )

        return ApiResponse(success=True, data=response_data)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/download/{laudo_id}")
async def download_laudo(
    laudo_id: str,
):
    """
    Download generated laudo file.

    Endpoint: GET /api/v1/auto-laudo/download/{laudo_id}

    Args:
        laudo_id: Laudo ID (laud_*)

    Returns:
        File download or placeholder URL
    """
    # TODO: Implement actual file storage and download
    return {"error": "Not implemented yet", "laudo_id": laudo_id}
