"""
ESAJ API routes with circuit breaker status endpoint.

Provides /api/v1/esaj/* endpoints with resilience features.
"""

from fastapi import APIRouter, HTTPException
from app.shared.schemas.api_response import ApiResponse
from app.modules.esaj.services.esaj_service import EsajService
from typing import Any, Dict

# Initialize service as global singleton
_esaj_service: EsajService = None


def get_esaj_service() -> EsajService:
    """Get or initialize ESAJ service."""
    global _esaj_service
    if _esaj_service is None:
        _esaj_service = EsajService()
    return _esaj_service


# Create router
esaj_router = APIRouter(
    prefix="/api/v1/esaj",
    tags=["esaj"],
)


@esaj_router.get("/status", response_model=ApiResponse[Dict[str, Any]])
async def get_esaj_status() -> ApiResponse[Dict[str, Any]]:
    """
    Get ESAJ service status and circuit breaker metrics.

    Returns:
        ApiResponse with service status:
        - circuit_breaker: Current state (closed/open/half-open) and metrics
        - fallback_cache: Cache statistics
        - available: Boolean indicating if service is available

    Useful for monitoring, alerting, and health checks.
    """
    try:
        service = get_esaj_service()
        status = service.get_status()

        return ApiResponse(
            success=True,
            data=status,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to get ESAJ status: {str(e)}",
        )


@esaj_router.get("/health")
async def esaj_health() -> Dict[str, Any]:
    """
    Simple health check for ESAJ service.

    Returns:
        Health status (for monitoring/load balancing)
    """
    service = get_esaj_service()
    status = service.get_status()

    health_status = "healthy" if status["available"] else "degraded"

    return {
        "status": health_status,
        "service": "esaj",
        "circuit_breaker_state": status["circuit_breaker"]["state"],
    }


@esaj_router.post("/reset-circuit-breaker")
async def reset_circuit_breaker() -> ApiResponse[Dict[str, str]]:
    """
    Reset circuit breaker to closed state.

    This endpoint is for administrative use during incidents
    when the service has recovered but the circuit is still open.

    Returns:
        ApiResponse confirming reset
    """
    try:
        service = get_esaj_service()
        service.reset_circuit_breaker()

        return ApiResponse(
            success=True,
            data={"message": "Circuit breaker reset to closed state"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset circuit breaker: {str(e)}",
        )


@esaj_router.post("/clear-cache")
async def clear_fallback_cache() -> ApiResponse[Dict[str, str]]:
    """
    Clear fallback cache.

    Removes all cached responses, useful after incidents or
    during maintenance when stale data is a concern.

    Returns:
        ApiResponse confirming cache cleared
    """
    try:
        service = get_esaj_service()
        service.clear_cache()

        return ApiResponse(
            success=True,
            data={"message": "Fallback cache cleared"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}",
        )
