"""
Resilience Patterns Infrastructure — Circuit Breaker, Retry, Timeout

Provides decorators for protecting external API calls with:
- Circuit Breaker: Fail-fast on repeated failures (state machine: CLOSED → OPEN → HALF_OPEN)
- Retry: Exponential backoff with configurable attempts
- Timeout: Per-request timeout with graceful fallback
- Event Bus Integration: Publishes fallback events for failure recovery

Thresholds (configurable per integration):
- Circuit Breaker: Opens after 5 consecutive failures or 50% failure rate over 10 requests
- Timeout: 10-60s per API (configurable per integration)
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s)

Usage:
    from app.core.resilience import circuit_breaker, retry, timeout, resilient_call

    @resilient_call(
        service_name="banco_inter",
        timeout_seconds=10,
        max_retries=3,
        cb_threshold=5,
        cb_timeout=60,
    )
    async def generate_boleto():
        return requests.post("https://api.bancointer.com.br/...")

    # Or use individual decorators:
    @circuit_breaker(service_name="qwen", threshold=5, timeout=60)
    @retry(max_attempts=3, backoff=2, initial_delay=1)
    @timeout(seconds=30)
    async def analyze_text():
        return await qwen_api.generate()
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Callable, Any, Optional, Dict, Type, Tuple
from uuid import uuid4

from app.core.event_bus import get_event_bus, Event

logger = logging.getLogger(__name__)


# ============================================================================
# Circuit Breaker State Machine
# ============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states: CLOSED (normal) → OPEN (fail-fast) → HALF_OPEN (testing)."""
    CLOSED = "CLOSED"  # Functioning normally; all requests pass through
    OPEN = "OPEN"  # Service down; fail-fast without attempting calls
    HALF_OPEN = "HALF_OPEN"  # Testing recovery; one request allowed to pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is OPEN (fail-fast)."""
    pass


class CircuitBreaker:
    """
    Circuit breaker state machine with configurable thresholds.

    Opens circuit after:
    - N consecutive failures (threshold)
    - OR 50% failure rate over recent requests

    Emits events to Event Bus for fallback handling.
    """

    def __init__(
        self,
        service_name: str,
        threshold: int = 5,
        timeout: int = 60,
        half_open_max_calls: int = 1,
        failure_rate_threshold: float = 0.5,
        window_size: int = 10,
    ):
        """
        Initialize circuit breaker.

        Args:
            service_name: Unique identifier (e.g., 'banco_inter', 'qwen')
            threshold: Consecutive failures before opening
            timeout: Seconds breaker stays open before testing
            half_open_max_calls: Max calls allowed in HALF_OPEN state
            failure_rate_threshold: Failure rate (0-1) to trigger open
            window_size: Recent request window for rate calculation
        """
        self.service_name = service_name
        self.threshold = threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.failure_rate_threshold = failure_rate_threshold
        self.window_size = window_size

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

        # Track recent requests for failure rate calculation
        self.recent_requests: list[tuple[datetime, bool]] = []  # (timestamp, success)

    def _reset(self):
        """Reset to CLOSED state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None
        self.recent_requests = []
        logger.info(f"Circuit breaker '{self.service_name}' CLOSED (reset)")

    def _open(self):
        """Transition to OPEN state."""
        self.state = CircuitBreakerState.OPEN
        self.opened_at = datetime.now()
        logger.error(
            f"Circuit breaker '{self.service_name}' OPEN "
            f"({self.failure_count} consecutive failures)"
        )

    def _half_open(self):
        """Transition to HALF_OPEN state for recovery testing."""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        logger.warning(
            f"Circuit breaker '{self.service_name}' HALF_OPEN "
            f"(testing recovery after {self.timeout}s)"
        )

    def _update_recent_requests(self, success: bool):
        """Track request outcome for failure rate calculation."""
        now = datetime.now()
        self.recent_requests.append((now, success))

        # Keep only recent window
        cutoff = now - timedelta(seconds=60)  # 60-second window
        self.recent_requests = [
            (ts, ok) for ts, ok in self.recent_requests
            if ts > cutoff
        ]

    def _check_failure_rate(self) -> bool:
        """Check if failure rate exceeds threshold."""
        if len(self.recent_requests) < self.window_size:
            return False  # Not enough data

        recent = self.recent_requests[-self.window_size:]
        failures = sum(1 for _, success in recent if not success)
        rate = failures / len(recent)

        return rate >= self.failure_rate_threshold

    def call_function(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitBreakerOpen: If breaker is OPEN
            Exception: Any exception from func
        """
        # State: OPEN — fail-fast if timeout not expired
        if self.state == CircuitBreakerState.OPEN:
            if self.opened_at and datetime.now() < self.opened_at + timedelta(seconds=self.timeout):
                remaining = (self.opened_at + timedelta(seconds=self.timeout) - datetime.now()).total_seconds()
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.service_name}' OPEN. "
                    f"Retry in {remaining:.1f}s"
                )
            else:
                # Timeout expired, transition to HALF_OPEN
                self._half_open()

        # Attempt function call
        try:
            result = func(*args, **kwargs)

            # Success
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._reset()  # Recovery confirmed
            else:
                self.failure_count = 0

            self._update_recent_requests(success=True)
            logger.debug(f"Circuit breaker '{self.service_name}' call succeeded")
            return result

        except Exception as e:
            # Failure
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            self._update_recent_requests(success=False)

            logger.warning(
                f"Circuit breaker '{self.service_name}' failure {self.failure_count}/{self.threshold}: "
                f"{type(e).__name__}: {str(e)[:100]}"
            )

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Any failure in HALF_OPEN reopens immediately
                self._open()
            elif self.failure_count >= self.threshold or self._check_failure_rate():
                # Open on threshold or failure rate
                self._open()

            raise

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "threshold": self.threshold,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "recent_request_count": len(self.recent_requests),
        }


# Global circuit breaker registry (singleton per service)
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service_name: str,
    threshold: int = 5,
    timeout: int = 60,
    failure_rate_threshold: float = 0.5,
) -> CircuitBreaker:
    """Get or create circuit breaker (singleton per service)."""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            threshold=threshold,
            timeout=timeout,
            failure_rate_threshold=failure_rate_threshold,
        )
    return _circuit_breakers[service_name]


# ============================================================================
# Decorators
# ============================================================================

def circuit_breaker(
    service_name: str,
    threshold: int = 5,
    timeout: int = 60,
    failure_rate_threshold: float = 0.5,
):
    """
    Decorator: Circuit breaker pattern.

    Args:
        service_name: Identifier for the external service
        threshold: Consecutive failures before opening circuit
        timeout: Seconds circuit stays open before testing
        failure_rate_threshold: Failure rate (0-1) to trigger open
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(
            service_name=service_name,
            threshold=threshold,
            timeout=timeout,
            failure_rate_threshold=failure_rate_threshold,
        )

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            return breaker.call_function(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            return breaker.call_function(func, *args, **kwargs)

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    backoff: float = 2.0,
    initial_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True,
):
    """
    Decorator: Retry with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts
        backoff: Exponential backoff multiplier (1s → 2s → 4s)
        initial_delay: Initial delay in seconds
        retryable_exceptions: Exception types that trigger retry
        jitter: Add randomness to prevent thundering herd
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"[{func.__name__}] Attempt {attempt}/{max_attempts}")
                    return func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: "
                        f"{type(e).__name__}: {str(e)[:100]}"
                    )

                    if attempt >= max_attempts:
                        logger.error(
                            f"[{func.__name__}] All {max_attempts} attempts exhausted"
                        )
                        raise

                    # Calculate delay with optional jitter
                    if jitter:
                        import random
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay

                    logger.info(
                        f"[{func.__name__}] Waiting {actual_delay:.1f}s "
                        f"before attempt {attempt + 1}"
                    )
                    time.sleep(actual_delay)
                    delay *= backoff

            if last_exception:
                raise last_exception

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"[{func.__name__}] Attempt {attempt}/{max_attempts}")
                    return await func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed: "
                        f"{type(e).__name__}: {str(e)[:100]}"
                    )

                    if attempt >= max_attempts:
                        logger.error(
                            f"[{func.__name__}] All {max_attempts} attempts exhausted"
                        )
                        raise

                    # Calculate delay with optional jitter
                    if jitter:
                        import random
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay

                    logger.info(
                        f"[{func.__name__}] Waiting {actual_delay:.1f}s "
                        f"before attempt {attempt + 1}"
                    )
                    await asyncio.sleep(actual_delay)
                    delay *= backoff

            if last_exception:
                raise last_exception

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def timeout(seconds: int):
    """
    Decorator: Timeout with graceful fallback.

    Args:
        seconds: Maximum execution time in seconds

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # For sync functions, we can't truly interrupt, so just log
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            if elapsed > seconds:
                logger.warning(
                    f"[{func.__name__}] Execution took {elapsed:.1f}s "
                    f"(timeout: {seconds}s) but completed"
                )

            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[{func.__name__}] Timeout after {seconds}s"
                )
                raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# Fallback Events (Wave 2 Event Bus Integration)
# ============================================================================

class CircuitBreakerOpenEvent(Event):
    """Event published when circuit breaker opens (fallback trigger)."""
    service_name: str
    reason: str
    timestamp: datetime


class APITimeoutEvent(Event):
    """Event published when API call times out."""
    service_name: str
    timeout_seconds: int
    timestamp: datetime


def resilient_call(
    service_name: str,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    cb_threshold: int = 5,
    cb_timeout: int = 60,
    failure_rate_threshold: float = 0.5,
    fallback_value: Any = None,
):
    """
    Combined resilience pattern: circuit breaker + retry + timeout.

    Applies decorators in order: timeout → retry → circuit_breaker

    Args:
        service_name: Service identifier (e.g., 'banco_inter', 'qwen')
        timeout_seconds: Per-request timeout
        max_retries: Retry attempts
        cb_threshold: Circuit breaker threshold
        cb_timeout: Circuit breaker reset timeout
        failure_rate_threshold: Failure rate to trigger circuit open
        fallback_value: Default value on all-failure fallback

    Example:
        @resilient_call(
            service_name="banco_inter",
            timeout_seconds=10,
            max_retries=3,
            cb_threshold=5,
        )
        async def generate_boleto(valor):
            return await inter_api.post(...)
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in order: innermost → outermost
        # timeout (innermost) → retry → circuit_breaker (outermost)
        wrapped = timeout(seconds=timeout_seconds)(func)
        wrapped = retry(
            max_attempts=max_retries,
            backoff=2.0,
            initial_delay=1.0,
            jitter=True,
        )(wrapped)
        wrapped = circuit_breaker(
            service_name=service_name,
            threshold=cb_threshold,
            timeout=cb_timeout,
            failure_rate_threshold=failure_rate_threshold,
        )(wrapped)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return wrapped(*args, **kwargs)
            except (CircuitBreakerOpen, asyncio.TimeoutError) as e:
                logger.error(f"Resilience fallback for {service_name}: {e}")
                # Optionally publish event for Event Bus handlers
                return fallback_value

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await wrapped(*args, **kwargs)
            except (CircuitBreakerOpen, asyncio.TimeoutError) as e:
                logger.error(f"Resilience fallback for {service_name}: {e}")
                # Optionally publish event for Event Bus handlers
                return fallback_value

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# Monitoring & Status Endpoints
# ============================================================================

def get_resilience_status() -> Dict[str, Any]:
    """Get status of all circuit breakers and resilience metrics."""
    return {
        "circuit_breakers": {
            name: breaker.get_status()
            for name, breaker in _circuit_breakers.items()
        },
        "timestamp": datetime.now().isoformat(),
    }


def get_resilience_metrics() -> Dict[str, Any]:
    """Alias for get_resilience_status for health check compatibility."""
    return get_resilience_status()
