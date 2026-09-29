"""
Router for deslocamento (travel distance/displacement) tools.

Endpoints:
- POST /api/v1/deslocamento/calcular: Calculate travel distance + toll + flight comparison
- GET /api/v1/deslocamento/pedagio: Get real-time toll from RotasBrasil API

Combined from:
- deslocamento_v2.py (main calculation endpoint)
- deslocamento_pedagio.py (toll API endpoint)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.database import get_db
from app.decorators.require_feature import require_feature_flag
from app.shared.exceptions import ExternalServiceException
from .schemas import DeslocamentoInput, DeslocamentoResponse, PedagioInput, PedagioResponse
from .service import calcular_deslocamento_completo, calcular_pedagio_rotasbrasil

router = APIRouter(prefix="/api/v1/deslocamento", tags=["deslocamento"])


@router.post(
    "/calcular",
    response_model=DeslocamentoResponse,
    summary="Calculate travel distance with toll and flight comparison",
    description="Calcula deslocamento: rota Google Maps + pedágio automático + comparativo avião"
)
async def calcular_deslocamento(
    input: DeslocamentoInput,
    db: Session = Depends(get_db)
):
    """
    Calculate travel distance and cost.

    Returns:
    - Distance and time (round trip or one-way)
    - Toll calculation (manual or automatic)
    - Flight comparison (if distance > 600km)
    - Cost breakdown and recommendations

    Args:
        input: Origin, destination, round-trip flag, optional manual toll
        db: Database session (optional dependency)

    Returns:
        Complete displacement calculation with comparisons
    """
    try:
        result = await calcular_deslocamento_completo(
            origem=input.origem,
            destino=input.destino,
            ida_volta=input.ida_volta,
            pedagio_manual=input.pedagio_manual
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao calcular deslocamento: {str(e)}"
        )


@router.get(
    "/pedagio",
    response_model=PedagioResponse,
    summary="Get real-time toll from RotasBrasil API",
    description="Calcula pedágio em tempo real via API RotasBrasil"
)
async def get_pedagio(
    origem: str,
    destino: str,
    veiculo: str = "caminhao",
    eixos: int = 6
):
    """
    Calculate toll in real-time using RotasBrasil API.

    This endpoint queries the RotasBrasil service for accurate toll rates
    based on vehicle type and axle count.

    Args:
        origem: Origin city (e.g., "Curitiba,PR" or postal code "88525-600")
        destino: Destination city (e.g., "Florianópolis,SC")
        veiculo: Vehicle type (caminhao, onibus, carro, moto)
        eixos: Number of axles (2-6)

    Returns:
        Toll details including one-way and round-trip amounts, distance, travel time

    Raises:
        HTTPException 503: If RotasBrasil service is unavailable
        HTTPException 500: If response parsing fails
    """
    try:
        result = await calcular_pedagio_rotasbrasil(
            origem=origem,
            destino=destino,
            veiculo=veiculo,
            eixos=eixos
        )
        return result
    except Exception as e:
        error_msg = str(e)
        if "indisponível" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Serviço de pedágio indisponível"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=error_msg if error_msg else "Erro ao calcular pedágio"
            )
