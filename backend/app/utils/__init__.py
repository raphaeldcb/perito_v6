"""Utilitários de resiliência e robustez.

Exporta:
- retry: decorator para retry com backoff exponencial
- CircuitBreaker: proteção de APIs com estados CLOSED/OPEN/HALF_OPEN
- get_circuit_breaker: factory de circuit breakers reutilizáveis
"""

from app.utils.retry import retry, RetryExhausted
from app.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
    get_circuit_breaker,
    circuit_breaker_status,
)

__all__ = [
    "retry",
    "RetryExhausted",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitBreakerState",
    "get_circuit_breaker",
    "circuit_breaker_status",
]
