"""
Laudos routes — API endpoints for CRUD, generation, and download.

Endpoints:
- LA-01: POST /laudos — Create laudo (draft)
- LA-02: PUT /laudos/{id} — Update laudo
- LA-03: POST /laudos/{id}/transition — Transition status
- LA-04: POST /laudos/{id}/generate-docx — Generate DOCX
- LA-05: GET /laudos/{id}/download — Download DOCX/PDF
- LA-06: GET /laudos?processo_id=X — List by processo
- LA-07: GET /laudos/{id} — Get laudo detail
- LA-08: POST /laudos/templates — Create template
- LA-09: GET /laudos/templates — List templates
- LA-10: DELETE /laudos/{id} — Soft delete laudo
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.database import get_db
from app.shared.schemas import ApiResponse
from app.shared.exceptions import PeritoException
from app.modules.laudos.models import LaudoStatusEnum, LaudoTipoEnum
from app.modules.laudos.schemas import (
    LaudoSchema,
    LaudoCreateRequest,
    LaudoUpdateRequest,
    LaudoStatusTransitionRequest,
    LaudoGenerateRequest,
    LaudoDownloadResponse,
    LaudoTemplateSchema,
    LaudoTemplateCreateRequest,
    LaudoListResponse,
)
from app.modules.laudos.services import (
    LaudoService,
    LaudoGeneratorService,
    LaudoPdfService,
)
from app.modules.laudos.repositories import LaudoTemplateRepository


router = APIRouter(prefix="/laudos", tags=["laudos"])


def _handle_exception(exc: Exception):
    """Convert PeritoException to HTTPException."""
    if isinstance(exc, PeritoException):
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.error_code,
                "detail": exc.detail,
                "context": exc.context,
            },
        )
    raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=ApiResponse[LaudoSchema], status_code=201, summary="LA-01: Create Laudo (Draft)")
async def create_laudo(
    req: LaudoCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LaudoSchema]:
    """Create new Laudo in RASCUNHO status."""
    try:
        service = LaudoService(db)
        laudo = service.create_draft(
            numero=req.numero,
            processo_id=req.processo_id,
            tipo=req.tipo,
            template_id=req.template_id,
            conteudo=req.conteudo,
        )
        return ApiResponse(success=True, data=LaudoSchema.from_orm(laudo))
    except Exception as e:
        _handle_exception(e)


@router.get("/{laudo_id}", response_model=ApiResponse[LaudoSchema], summary="LA-07: Get Laudo Detail")
async def get_laudo(
    laudo_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[LaudoSchema]:
    """Get Laudo by ID."""
    try:
        service = LaudoService(db)
        laudo = service.get_laudo(laudo_id)
        return ApiResponse(success=True, data=LaudoSchema.from_orm(laudo))
    except Exception as e:
        _handle_exception(e)


@router.put("/{laudo_id}", response_model=ApiResponse[LaudoSchema], summary="LA-02: Update Laudo")
async def update_laudo(
    laudo_id: int,
    req: LaudoUpdateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LaudoSchema]:
    """Update Laudo content (only in RASCUNHO/REVISION status)."""
    try:
        service = LaudoService(db)
        if req.conteudo:
            laudo = service.update_content(laudo_id, req.conteudo)
        else:
            # For other fields, use repository directly
            from app.modules.laudos.repositories import LaudoRepository
            repo = LaudoRepository(db)
            update_data = req.dict(exclude_none=True)
            laudo = repo.update(laudo_id, **update_data)
        return ApiResponse(success=True, data=LaudoSchema.from_orm(laudo))
    except Exception as e:
        _handle_exception(e)


@router.post("/{laudo_id}/transition", response_model=ApiResponse[LaudoSchema], summary="LA-03: Transition Status")
async def transition_status(
    laudo_id: int,
    req: LaudoStatusTransitionRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LaudoSchema]:
    """Transition Laudo status via state machine."""
    try:
        service = LaudoService(db)
        laudo = service.transition_status(
            laudo_id,
            req.new_status,
            req.motivo,
        )
        return ApiResponse(success=True, data=LaudoSchema.from_orm(laudo))
    except Exception as e:
        _handle_exception(e)


@router.post("/{laudo_id}/generate-docx", response_model=ApiResponse[dict], summary="LA-04: Generate DOCX")
async def generate_docx(
    laudo_id: int,
    req: LaudoGenerateRequest = LaudoGenerateRequest(),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """Generate DOCX file from template + content."""
    try:
        service = LaudoGeneratorService(db)
        filepath = service.generate_docx(
            laudo_id,
            template_id=req.template_id,
            conteudo_override=req.conteudo,
        )
        return ApiResponse(
            success=True,
            data={
                "laudo_id": laudo_id,
                "arquivo_path": filepath,
                "formato": "docx",
                "tamanho_bytes": os.path.getsize(filepath),
            },
        )
    except Exception as e:
        _handle_exception(e)


@router.post("/{laudo_id}/generate-pdf", response_model=ApiResponse[dict], summary="Generate PDF from Laudo DOCX")
async def generate_pdf(
    laudo_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """Generate PDF from existing Laudo DOCX."""
    try:
        service = LaudoPdfService(db)
        filepath = service.generate_pdf_from_laudo(laudo_id)
        return ApiResponse(
            success=True,
            data={
                "laudo_id": laudo_id,
                "arquivo_path": filepath,
                "formato": "pdf",
                "tamanho_bytes": os.path.getsize(filepath),
            },
        )
    except Exception as e:
        _handle_exception(e)


@router.get("/{laudo_id}/download", response_model=ApiResponse[LaudoDownloadResponse], summary="LA-05: Download")
async def download_laudo(
    laudo_id: int,
    formato: str = Query("docx", regex="^(docx|pdf)$"),
    db: Session = Depends(get_db),
) -> ApiResponse[LaudoDownloadResponse]:
    """Get download metadata for Laudo DOCX or PDF."""
    try:
        from app.modules.laudos.repositories import LaudoRepository
        repo = LaudoRepository(db)
        laudo = repo.get_by_id(laudo_id)
        if not laudo:
            raise HTTPException(status_code=404, detail="Laudo não encontrado")

        if formato == "docx":
            if not laudo.arquivo_docx_path or not os.path.exists(laudo.arquivo_docx_path):
                raise HTTPException(status_code=404, detail="DOCX não gerado")
            filepath = laudo.arquivo_docx_path
        else:  # pdf
            if not laudo.arquivo_pdf_path or not os.path.exists(laudo.arquivo_pdf_path):
                raise HTTPException(status_code=404, detail="PDF não gerado")
            filepath = laudo.arquivo_pdf_path

        return ApiResponse(
            success=True,
            data=LaudoDownloadResponse(
                laudo_id=laudo_id,
                arquivo_path=filepath,
                formato=formato,
                tamanho_bytes=os.path.getsize(filepath),
                data_criacao=laudo.created_at,
            ),
        )
    except Exception as e:
        _handle_exception(e)


@router.get("", response_model=ApiResponse[list[LaudoListResponse]], summary="LA-06: List Laudos")
async def list_laudos(
    processo_id: int = Query(None),
    status: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> ApiResponse[list[LaudoListResponse]]:
    """List Laudos with filters."""
    try:
        service = LaudoService(db)
        if processo_id:
            laudos, total = service.list_by_processo(processo_id, skip, limit)
        elif status:
            laudos, total = service.list_by_status(LaudoStatusEnum(status), skip, limit)
        else:
            # Default: all laudos
            from app.modules.laudos.repositories import LaudoRepository
            repo = LaudoRepository(db)
            query = repo.db.query(repo.db.query(repo.db.query.__class__))  # Fallback
            laudos = []
            total = 0

        return ApiResponse(
            success=True,
            data=[LaudoListResponse.from_orm(l) for l in laudos],
            meta={"total": total, "skip": skip, "limit": limit},
        )
    except Exception as e:
        _handle_exception(e)


@router.delete("/{laudo_id}", response_model=ApiResponse[dict], summary="LA-10: Soft Delete Laudo")
async def delete_laudo(
    laudo_id: int,
    deletado_por_id: int = Query(...),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """Soft delete (mark deleted) Laudo."""
    try:
        service = LaudoService(db)
        laudo = service.soft_delete(laudo_id, deletado_por_id)
        return ApiResponse(
            success=True,
            data={"laudo_id": laudo_id, "deletado": True},
        )
    except Exception as e:
        _handle_exception(e)


# Template endpoints

@router.post("/templates", response_model=ApiResponse[LaudoTemplateSchema], status_code=201, summary="LA-08: Create Template")
async def create_template(
    req: LaudoTemplateCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LaudoTemplateSchema]:
    """Create new Laudo template."""
    try:
        repo = LaudoTemplateRepository(db)
        template = repo.create(
            nome=req.nome,
            tipo=req.tipo,
            conteudo=req.conteudo,
            descricao=req.descricao,
            ativo=True,
        )
        return ApiResponse(success=True, data=LaudoTemplateSchema.from_orm(template))
    except Exception as e:
        _handle_exception(e)


@router.get("/templates", response_model=ApiResponse[list[LaudoTemplateSchema]], summary="LA-09: List Templates")
async def list_templates(
    db: Session = Depends(get_db),
) -> ApiResponse[list[LaudoTemplateSchema]]:
    """List all Laudo templates."""
    try:
        repo = LaudoTemplateRepository(db)
        templates, _ = repo.list_all()
        return ApiResponse(
            success=True,
            data=[LaudoTemplateSchema.from_orm(t) for t in templates],
        )
    except Exception as e:
        _handle_exception(e)
