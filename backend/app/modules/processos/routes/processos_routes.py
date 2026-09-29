"""Routes for Processos module — PR-01 to PR-15."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.services import get_db
from app.middleware import get_current_user
from app.models import User
from app.shared import (
    ApiResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.shared.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    ConflictException,
)
from app.modules.processos.schemas import (
    ProcessoCreateSchema,
    ProcessoUpdateSchema,
    ProcessoResponseSchema,
    ProcessoListSchema,
    IntimacaoCreateSchema,
    IntimacaoUpdateSchema,
    IntimacaoResponseSchema,
    IntimacaoListSchema,
)
from app.modules.processos.services import ProcessoService, IntimacaoService

router = APIRouter(prefix="/api/v1/processos", tags=["processos"])


# ============================================================================
# PROCESSO ENDPOINTS (PR-01 to PR-10)
# ============================================================================

# PR-01: GET /processos (list all)
@router.get("", response_model=PaginatedResponse[ProcessoListSchema])
async def list_processos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-01: List all processos with pagination."""
    service = ProcessoService(db)
    processos, total = await service.list_processos(skip=skip, limit=limit)

    return PaginatedResponse[ProcessoListSchema](
        success=True,
        data=[ProcessoListSchema.model_validate(p) for p in processos],
        pagination=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_items=total,
            total_pages=(total + limit - 1) // limit,
            has_next=(skip + limit) < total,
            has_previous=skip > 0,
        ),
    )


# PR-02: POST /processos (create)
@router.post("", response_model=ApiResponse[ProcessoResponseSchema], status_code=201)
async def create_processo(
    data: ProcessoCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-02: Create a new processo."""
    service = ProcessoService(db)
    resultado = await service.create_processo(data)

    return ApiResponse(
        success=True,
        data=resultado,
    )


# PR-03: GET /processos/{id} (get by id)
@router.get("/{id}", response_model=ApiResponse[ProcessoResponseSchema])
async def get_processo(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-03: Get a processo by ID."""
    service = ProcessoService(db)
    resultado = await service.get_processo(id)

    return ApiResponse(
        success=True,
        data=resultado,
    )


# PR-04: PATCH /processos/{id} (update)
@router.patch("/{id}", response_model=ApiResponse[ProcessoResponseSchema])
async def update_processo(
    id: int,
    data: ProcessoUpdateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-04: Update a processo."""
    service = ProcessoService(db)
    resultado = await service.update_processo(id, data)

    return ApiResponse(
        success=True,
        data=resultado,
    )


# PR-05: DELETE /processos/{id} (delete)
@router.delete("/{id}", response_model=ApiResponse[dict])
async def delete_processo(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-05: Delete a processo."""
    service = ProcessoService(db)
    await service.delete_processo(id)

    return ApiResponse(
        success=True,
        data={"message": f"Processo {id} deleted successfully"},
    )


# PR-06: GET /processos/search (search)
@router.get("/search/query", response_model=PaginatedResponse[ProcessoListSchema])
async def search_processos(
    q: str = Query(..., min_length=2, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-06: Search processos by text (numero_cnj, titulo, autor, reu)."""
    service = ProcessoService(db)
    processos, total = await service.search_processos(query=q, skip=skip, limit=limit)

    return PaginatedResponse[ProcessoListSchema](
        success=True,
        data=[ProcessoListSchema.model_validate(p) for p in processos],
        pagination=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_items=total,
            total_pages=(total + limit - 1) // limit,
            has_next=(skip + limit) < total,
            has_previous=skip > 0,
        ),
    )


# PR-07: GET /processos/filter (filter by comarca, vara, area, status)
@router.get("/filter/advanced", response_model=PaginatedResponse[ProcessoListSchema])
async def filter_processos(
    comarca: Optional[str] = Query(None),
    vara: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-07: Filter processos by comarca, vara, area, status."""
    service = ProcessoService(db)
    processos, total = await service.list_with_filters(
        skip=skip,
        limit=limit,
        comarca=comarca,
        vara=vara,
        area=area,
        status=status,
    )

    return PaginatedResponse[ProcessoListSchema](
        success=True,
        data=[ProcessoListSchema.model_validate(p) for p in processos],
        pagination=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_items=total,
            total_pages=(total + limit - 1) // limit,
            has_next=(skip + limit) < total,
            has_previous=skip > 0,
        ),
    )


# PR-08: GET /processos/by-comarca/{comarca}
@router.get("/by-comarca/{comarca}", response_model=PaginatedResponse[ProcessoListSchema])
async def list_by_comarca(
    comarca: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-08: List processos filtered by comarca."""
    service = ProcessoService(db)
    processos, total = await service.list_by_comarca(comarca, skip=skip, limit=limit)

    return PaginatedResponse[ProcessoListSchema](
        success=True,
        data=[ProcessoListSchema.model_validate(p) for p in processos],
        pagination=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_items=total,
            total_pages=(total + limit - 1) // limit,
            has_next=(skip + limit) < total,
            has_previous=skip > 0,
        ),
    )


# PR-09: GET /processos/stats
@router.get("/stats/overview", response_model=ApiResponse[dict])
async def get_processo_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-09: Get processo statistics."""
    service = ProcessoService(db)
    stats = await service.get_stats()

    return ApiResponse(
        success=True,
        data=stats,
    )


# PR-10: GET /processos/values/{field} (get distinct values)
@router.get("/values/{field}", response_model=ApiResponse[dict])
async def get_distinct_values(
    field: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-10: Get distinct values for a field (comarca, vara, setor, status)."""
    service = ProcessoService(db)

    values = []
    if field == "comarca":
        values = await service.get_distinct_comarcas()
    elif field == "vara":
        values = await service.get_distinct_varas()
    elif field == "setor":
        values = await service.get_distinct_setores()
    elif field == "status":
        values = await service.get_distinct_statuses()
    else:
        raise ValidationException(
            error_code="INVALID_FIELD",
            detail=f"Invalid field: {field}. Allowed: comarca, vara, setor, status"
        )

    return ApiResponse(
        success=True,
        data={field: values},
    )


# ============================================================================
# INTIMACAO ENDPOINTS (PR-11 to PR-15)
# ============================================================================

# PR-11: GET /processos/{processo_id}/intimacoes (list by processo)
@router.get("/{processo_id}/intimacoes", response_model=PaginatedResponse[IntimacaoListSchema])
async def list_intimacoes_by_processo(
    processo_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-11: List intimacoes for a processo."""
    service = IntimacaoService(db)
    intimacoes, total = await service.list_by_processo(
        processo_id=processo_id,
        skip=skip,
        limit=limit,
    )

    return PaginatedResponse[IntimacaoListSchema](
        success=True,
        data=[IntimacaoListSchema.model_validate(i) for i in intimacoes],
        pagination=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_items=total,
            total_pages=(total + limit - 1) // limit,
            has_next=(skip + limit) < total,
            has_previous=skip > 0,
        ),
    )


# PR-12: POST /processos/{processo_id}/intimacoes (create)
@router.post("/{processo_id}/intimacoes", response_model=ApiResponse[IntimacaoResponseSchema], status_code=201)
async def create_intimacao(
    processo_id: int,
    data: IntimacaoCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-12: Create a new intimacao for a processo."""
    # Ensure processo_id matches
    data.processo_id = processo_id

    service = IntimacaoService(db)
    resultado = await service.create_intimacao(data)

    return ApiResponse(
        success=True,
        data=resultado,
    )


# PR-13: GET /processos/intimacoes/{id} (get by id)
@router.get("/intimacoes/{id}", response_model=ApiResponse[IntimacaoResponseSchema])
async def get_intimacao(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-13: Get an intimacao by ID."""
    service = IntimacaoService(db)
    resultado = await service.get_intimacao(id)

    return ApiResponse(
        success=True,
        data=resultado,
    )


# PR-14: PATCH /processos/intimacoes/{id} (update)
@router.patch("/intimacoes/{id}", response_model=ApiResponse[IntimacaoResponseSchema])
async def update_intimacao(
    id: int,
    data: IntimacaoUpdateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-14: Update an intimacao."""
    service = IntimacaoService(db)
    resultado = await service.update_intimacao(id, data)

    return ApiResponse(
        success=True,
        data=resultado,
    )


# PR-15: DELETE /processos/intimacoes/{id} (delete)
@router.delete("/intimacoes/{id}", response_model=ApiResponse[dict])
async def delete_intimacao(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PR-15: Delete an intimacao."""
    service = IntimacaoService(db)
    await service.delete_intimacao(id)

    return ApiResponse(
        success=True,
        data={"message": f"Intimacao {id} deleted successfully"},
    )
