"""Calculator routes for deslocamento and juros endpoints."""

from fastapi import APIRouter, HTTPException
from decimal import Decimal

from app.shared import ApiResponse, ValidationException
from .schemas import (
    DeslocamentoRequest,
    DeslocamentoResponse,
    JurosRequest,
    JurosResponse,
)
from .service import get_calculator_service

router = APIRouter(prefix="/api/v1/ferramentas/calculos", tags=["ferramentas"])


@router.post("/deslocamento", response_model=ApiResponse[DeslocamentoResponse])
async def calculate_deslocamento(request: DeslocamentoRequest) -> ApiResponse:
    """
    Calculate deslocamento (travel expense).

    Endpoint: POST /api/v1/ferramentas/calculos/deslocamento

    Calculates travel cost based on distance and toll.

    Args:
        request: DeslocamentoRequest with distance_km, toll_cost, rate_per_km

    Returns:
        ApiResponse with calculated travel cost breakdown
    """
    try:
        service = get_calculator_service()
        result = service.calculate_deslocamento(
            distance_km=request.distance_km,
            toll_cost=request.toll_cost,
            rate_per_km=request.rate_per_km,
        )

        response_data = DeslocamentoResponse(**result)
        return ApiResponse(success=True, data=response_data)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.post("/juros", response_model=ApiResponse[JurosResponse])
async def calculate_juros(request: JurosRequest) -> ApiResponse:
    """
    Calculate juros (interest).

    Endpoint: POST /api/v1/ferramentas/calculos/juros

    Calculates simple interest on a principal amount.

    Args:
        request: JurosRequest with principal, rate_per_month, days

    Returns:
        ApiResponse with calculated interest breakdown
    """
    try:
        service = get_calculator_service()
        result = service.calculate_juros(
            principal=request.principal,
            rate_per_month=request.rate_per_month,
            days=request.days,
        )

        response_data = JurosResponse(**result)
        return ApiResponse(success=True, data=response_data)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
