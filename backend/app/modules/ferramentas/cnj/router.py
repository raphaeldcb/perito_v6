"""CNJ routes for CNJ number parsing and validation."""

from fastapi import APIRouter, HTTPException

from app.shared import ApiResponse
from .schemas import CNJRequest, CNJResponse
from .service import get_cnj_service

router = APIRouter(prefix="/api/v1/ferramentas/cnj", tags=["ferramentas"])


@router.post("/parse", response_model=ApiResponse[CNJResponse])
async def parse_cnj_number(request: CNJRequest) -> ApiResponse:
    """
    Parse and validate CNJ process number.

    Endpoint: POST /api/v1/ferramentas/cnj/parse

    Extracts components from a CNJ (Conselho Nacional de Justiça) process number.

    Args:
        request: CNJRequest with cnj_number (25 digits)

    Returns:
        ApiResponse with:
            - valid: Whether the CNJ number is valid
            - parsed: Components if valid (sequential, verification, year, segment, court, state)
            - error: Error message if invalid
    """
    try:
        service = get_cnj_service()
        result = service.validate_cnj(request.cnj_number)

        response = CNJResponse(**result)
        return ApiResponse(success=result["valid"], data=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CNJ parsing error: {str(e)}")


@router.get("/validate/{cnj_number}", response_model=ApiResponse[CNJResponse])
async def validate_cnj(cnj_number: str) -> ApiResponse:
    """
    Validate CNJ process number (GET endpoint).

    Endpoint: GET /api/v1/ferramentas/cnj/validate/{cnj_number}

    Args:
        cnj_number: 25-digit CNJ process number

    Returns:
        ApiResponse with validation result and parsed components if valid
    """
    try:
        service = get_cnj_service()
        result = service.validate_cnj(cnj_number)

        response = CNJResponse(**result)
        return ApiResponse(success=result["valid"], data=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CNJ validation error: {str(e)}")
