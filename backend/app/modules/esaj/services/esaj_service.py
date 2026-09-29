"""
ESAJ service with circuit breaker and fallback integration.

Provides resilient API client for ESAJ queries with automatic
failure handling and graceful degradation.
"""

import httpx
from typing import Any, Dict, Optional
from datetime import datetime
from app.modules.esaj.config import EsajConfig
from app.modules.esaj.services.circuit_breaker import CircuitBreaker
from app.modules.esaj.services.fallback_service import FallbackService
from app.shared.exceptions import ExternalServiceException


class EsajService:
    """
    ESAJ API service with circuit breaker and fallback.

    Provides resilient queries to ESAJ API with:
    - Circuit breaker pattern for fail-fast behavior
    - Response caching for fallback
    - Graceful degradation when service is unavailable
    """

    def __init__(self, config: Optional[EsajConfig] = None):
        """
        Initialize ESAJ service.

        Args:
            config: ESAJ configuration (loaded from env if not provided)
        """
        self.config = config or EsajConfig()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
        )
        self.fallback_service = FallbackService(cache_ttl_seconds=3600)

    def get_processo(self, cnj: str) -> Dict[str, Any]:
        """
        Query ESAJ for processo information by CNJ number.

        Args:
            cnj: CNJ processo number

        Returns:
            Processo data

        Raises:
            ExternalServiceException: If API call fails
        """
        try:
            # Try to call with circuit breaker protection
            result = self.circuit_breaker.call(self._make_request, cnj)
            # Cache successful response
            self.fallback_service.cache_response(cnj, result)
            return result
        except Exception as e:
            # Try to return fallback
            if str(e).startswith("Circuit breaker"):
                return self.fallback_service.get_fallback_response(cnj)
            raise ExternalServiceException(
                f"Failed to query ESAJ for processo {cnj}: {str(e)}",
                context={"cnj": cnj, "error": str(e)},
            )

    def _make_request(self, cnj: str) -> Dict[str, Any]:
        """
        Make actual HTTP request to ESAJ API.

        Args:
            cnj: CNJ processo number

        Returns:
            API response data

        Raises:
            Exception: If request fails
        """
        endpoint = f"api/v1/processo/{cnj}"
        url = self.config.get_url(endpoint)

        try:
            response = httpx.get(
                url,
                timeout=self.config.timeout_seconds,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"ESAJ API error: {str(e)}")

    def get_processo_safe(self, cnj: str) -> Dict[str, Any]:
        """
        Get processo with guaranteed response (cached or fallback).

        Never raises exceptions, always returns valid response structure.

        Args:
            cnj: CNJ processo number

        Returns:
            Processo data (cached, fallback, or real)
        """
        try:
            return self.get_processo(cnj)
        except Exception:
            # Return fallback even if circuit breaker error
            return self.fallback_service.get_fallback_response(cnj)

    def get_status(self) -> Dict[str, Any]:
        """
        Get service status for monitoring.

        Returns:
            Status dictionary with circuit breaker and cache info
        """
        cb_metrics = self.circuit_breaker.get_metrics()
        cache_stats = self.fallback_service.get_cache_stats()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "esaj",
            "available": self.circuit_breaker.state == "closed",
            "circuit_breaker": {
                "state": cb_metrics["state"],
                "failure_count": cb_metrics["failure_count"],
                "success_count": cb_metrics["success_count"],
                "total_calls": cb_metrics["total_calls"],
            },
            "fallback_cache": {
                "cached_items": cache_stats["cached_items"],
                "ttl_seconds": cache_stats["ttl_seconds"],
            },
        }

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker to closed state."""
        self.circuit_breaker.reset()

    def clear_cache(self) -> None:
        """Clear all fallback cache."""
        self.fallback_service.clear_cache()
