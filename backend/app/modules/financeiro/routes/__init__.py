"""
Financeiro module routes — FI-01 to FI-10 endpoints.

RESTful API for boleto management, payment tracking, and financial operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from app.services import get_db
from app.middleware import get_current_user
from app.models import User
from app.shared.schemas import ApiResponse, ErrorDetail

from app.modules.financeiro.models import Boleto, Nota, Honorario
from app.modules.financeiro.schemas import (
    BoletoCreate, BoletoUpdate, BoletoResponse,
    NotaCreate, NotaUpdate, NotaResponse,
    HonorarioCreate, HonorarioUpdate, HonorarioResponse,
)
from app.modules.financeiro.repositories import BoletoRepository
from app.modules.financeiro.services import BoletoService, ContaUnicaService
from app.shared.exceptions import ValidationException, ResourceNotFoundException

# Create router for financeiro module
router = APIRouter(prefix="/api/v1/financeiro", tags=["financeiro"])


# ============================================================================
# BOLETO ENDPOINTS (FI-01 to FI-06)
# ============================================================================

@router.post("/boletos", response_model=ApiResponse[BoletoResponse], status_code=status.HTTP_201_CREATED)
async def create_boleto(
    boleto_create: BoletoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-01: Create a new boleto.

    Generates a boleto in Banco Inter and creates local record.
    """
    try:
        repository = BoletoRepository(db)
        service = BoletoService(db, repository)

        boleto = await service.generate_boleto(
            processo_id=boleto_create.processo_id,
            valor=boleto_create.valor,
            vencimento=boleto_create.vencimento,
            descricao=boleto_create.descricao,
        )

        return ApiResponse(
            success=True,
            data=BoletoResponse.from_orm(boleto),
        )
    except ValidationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boletos/{boleto_id}", response_model=ApiResponse[BoletoResponse])
async def get_boleto(
    boleto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-02: Get boleto by ID.

    Retrieves boleto details and current status.
    """
    try:
        boleto = db.query(Boleto).filter(Boleto.id == boleto_id, Boleto.ativo == True).first()
        if not boleto:
            raise ResourceNotFoundException("Boleto não encontrado", error_code="BOLETO_NOT_FOUND")

        return ApiResponse(
            success=True,
            data=BoletoResponse.from_orm(boleto),
        )
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/boletos", response_model=ApiResponse[List[BoletoResponse]])
async def list_boletos(
    processo_id: Optional[int] = Query(None, description="Filter by processo_id"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-03: List boletos with filters.

    Supports filtering by processo_id and status with pagination.
    """
    query = db.query(Boleto).filter(Boleto.ativo == True)

    if processo_id:
        query = query.filter(Boleto.processo_id == processo_id)
    if status:
        query = query.filter(Boleto.status == status)

    boletos = query.offset(skip).limit(limit).all()

    return ApiResponse(
        success=True,
        data=[BoletoResponse.from_orm(b) for b in boletos],
    )


@router.patch("/boletos/{boleto_id}", response_model=ApiResponse[BoletoResponse])
async def update_boleto(
    boleto_id: int,
    boleto_update: BoletoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-04: Update boleto.

    Allows updating status, payment date, and discounts.
    """
    try:
        boleto = db.query(Boleto).filter(Boleto.id == boleto_id, Boleto.ativo == True).first()
        if not boleto:
            raise ResourceNotFoundException("Boleto não encontrado", error_code="BOLETO_NOT_FOUND")

        if boleto_update.status:
            boleto.status = boleto_update.status
        if boleto_update.data_pagamento:
            boleto.data_pagamento = boleto_update.data_pagamento
        if boleto_update.desconto is not None:
            boleto.desconto = boleto_update.desconto

        db.commit()
        db.refresh(boleto)

        return ApiResponse(
            success=True,
            data=BoletoResponse.from_orm(boleto),
        )
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/boletos/{boleto_id}/cancel", response_model=ApiResponse[BoletoResponse])
async def cancel_boleto(
    boleto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-05: Cancel a boleto.

    Cancels the boleto in Banco Inter and marks as canceled locally.
    """
    try:
        repository = BoletoRepository(db)
        service = BoletoService(db, repository)

        boleto = await service.cancel_boleto(boleto_id)

        return ApiResponse(
            success=True,
            data=BoletoResponse.from_orm(boleto),
        )
    except (ValidationException, ResourceNotFoundException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/boletos/{boleto_id}/sync-status", response_model=ApiResponse[BoletoResponse])
async def sync_boleto_status(
    boleto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-06: Sync boleto status from Banco Inter.

    Updates local boleto status based on Inter API data.
    """
    try:
        repository = BoletoRepository(db)
        service = BoletoService(db, repository)

        boleto = await service.sync_payment_status(boleto_id)

        return ApiResponse(
            success=True,
            data=BoletoResponse.from_orm(boleto),
        )
    except (ValidationException, ResourceNotFoundException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONTA ÚNICA ENDPOINTS (FI-07 to FI-08)
# ============================================================================

@router.post("/conta-unica/sync-payments", response_model=ApiResponse)
async def sync_conta_unica_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-07: Sync payments from Conta Única.

    Queries Conta Única API and updates all pending boletos.
    Returns sync summary: synced count, total payments, errors.
    """
    try:
        repository = BoletoRepository(db)
        service = ContaUnicaService(db, repository)

        result = await service.sync_payments()

        return ApiResponse(
            success=True,
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conta-unica/payment-status/{boleto_id}", response_model=ApiResponse)
async def get_conta_unica_payment_status(
    boleto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-08: Get payment status from Conta Única.

    Checks payment status for a specific boleto via Conta Única API.
    """
    try:
        repository = BoletoRepository(db)
        service = ContaUnicaService(db, repository)

        status = await service.get_payment_status(boleto_id)

        return ApiResponse(
            success=True,
            data=status,
        )
    except (ValidationException, ResourceNotFoundException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NOTA ENDPOINTS (FI-09)
# ============================================================================

@router.post("/notas", response_model=ApiResponse[NotaResponse], status_code=status.HTTP_201_CREATED)
async def create_nota(
    nota_create: NotaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-09: Create a new nota fiscal.

    Creates a nota entry linked to a processo.
    """
    try:
        nota = Nota(
            numero=nota_create.numero,
            processo_id=nota_create.processo_id,
            valor=nota_create.valor,
            descricao=nota_create.descricao,
            data_emissao=nota_create.data_emissao,
            nf_serie=nota_create.nf_serie,
            nf_numero=nota_create.nf_numero,
            nf_cnpj=nota_create.nf_cnpj,
        )

        db.add(nota)
        db.commit()
        db.refresh(nota)

        return ApiResponse(
            success=True,
            data=NotaResponse.from_orm(nota),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HONORÁRIO ENDPOINTS (FI-10)
# ============================================================================

@router.post("/honorarios", response_model=ApiResponse[HonorarioResponse], status_code=status.HTTP_201_CREATED)
async def create_honorario(
    honorario_create: HonorarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    FI-10: Create a new honorário entry.

    Creates a honorário record with calculated final value.
    """
    try:
        # Calculate final value: valor_base * (percentual / 100)
        valor_final = honorario_create.valor_base * (honorario_create.percentual / Decimal(100))

        honorario = Honorario(
            processo_id=honorario_create.processo_id,
            valor_base=honorario_create.valor_base,
            percentual=honorario_create.percentual,
            valor_final=valor_final,
            observacoes=honorario_create.observacoes,
        )

        db.add(honorario)
        db.commit()
        db.refresh(honorario)

        return ApiResponse(
            success=True,
            data=HonorarioResponse.from_orm(honorario),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
