"""
Shared exception base classes for PERITO v6 modular architecture.

All modules should raise exceptions inheriting from PeritoException
to ensure consistent error handling across the system.
"""

from typing import Optional, Any, Dict


class PeritoException(Exception):
    """
    Base exception for all PERITO system errors.

    Provides structured error information including:
    - error_code: Machine-readable error identifier
    - status_code: HTTP status code
    - detail: Human-readable error message
    - context: Additional error context data
    """

    error_code: str = "PERITO_ERROR"
    status_code: int = 500

    def __init__(
        self,
        detail: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.detail = detail
        self.error_code = error_code or self.__class__.error_code
        self.status_code = status_code or self.__class__.status_code
        self.context = context or {}
        super().__init__(self.detail)


class ValidationException(PeritoException):
    """Raised when input validation fails."""

    error_code = "VALIDATION_ERROR"
    status_code = 422


class AuthenticationException(PeritoException):
    """Raised when authentication fails."""

    error_code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationException(PeritoException):
    """Raised when user lacks required permissions."""

    error_code = "AUTHORIZATION_ERROR"
    status_code = 403


class ResourceNotFoundException(PeritoException):
    """Raised when a requested resource is not found."""

    error_code = "NOT_FOUND"
    status_code = 404


class ConflictException(PeritoException):
    """Raised when an operation conflicts with existing state."""

    error_code = "CONFLICT"
    status_code = 409


class ExternalServiceException(PeritoException):
    """Raised when an external service call fails."""

    error_code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502
