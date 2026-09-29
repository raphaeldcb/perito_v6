"""Shared exception classes for all modules."""

from .base import (
    PeritoException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    ExternalServiceException,
)

__all__ = [
    "PeritoException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "ResourceNotFoundException",
    "ConflictException",
    "ExternalServiceException",
]
