"""
Circuit breaker pattern implementation for ESAJ API resilience.

Implements fail-fast behavior with automatic recovery and state management.
"""

import time
from typing import TypeVar, Callable, Any, Dict
from datetime import datetime

T = TypeVar("T")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and calls are rejected."""

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external API calls.

    States:
    - closed: Normal operation, calls pass through
    - open: Too many failures, calls rejected immediately
    - half-open: Recovery phase, limited calls allowed

    Transitions:
    - closed → open: After failure_threshold failures
    - open → half-open: After recovery_timeout seconds
    - half-open → closed: After success_threshold successes
    - half-open → open: After any failure
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening (default: 3)
            recovery_timeout: Seconds before attempting recovery (default: 60)
            success_threshold: Successes needed in half-open to close (default: 2)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float = 0.0
        self.opened_at: float = time.time()  # Initialize to current time

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function return value

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Propagates exceptions from the function
        """
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half-open"
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open. Service unavailable. "
                    f"Retry after {self.recovery_timeout}s"
                )

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def record_success(self) -> None:
        """Record successful call."""
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
        elif self.state == "closed":
            # Track success in closed state
            self.success_count += 1

    def record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "closed":
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                self.opened_at = time.time()
        elif self.state == "half-open":
            self.state = "open"
            self.opened_at = time.time()

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has elapsed."""
        return (time.time() - self.opened_at) >= self.recovery_timeout

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get circuit breaker metrics.

        Returns:
            Dictionary with current metrics
        """
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.failure_count + self.success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "opened_at": datetime.fromtimestamp(self.opened_at).isoformat()
            if self.opened_at > 0
            else None,
        }

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.opened_at = 0.0
