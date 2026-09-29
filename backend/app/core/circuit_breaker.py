"""
Circuit Breaker backward compatibility wrapper.

This module re-exports from resilience.py for backward compatibility.
New code should import from resilience.py directly.
"""

from app.core.resilience import (
    CircuitBreakerState,
    CircuitBreakerOpen,
    CircuitBreaker,
    get_circuit_breaker,
    circuit_breaker,
)

__all__ = [
    "CircuitBreakerState",
    "CircuitBreakerOpen",
    "CircuitBreaker",
    "get_circuit_breaker",
    "circuit_breaker",
]
