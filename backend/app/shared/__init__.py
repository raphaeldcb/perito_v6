"""Shared layer for modular architecture.

All modules communicate via shared DTOs, exceptions, and base classes.
No direct imports between modules are allowed.

Contract-heavy, logic-light layer:
- No business logic
- No database queries
- Only type contracts and basic utilities
"""

from .exceptions import (
    PeritoException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    ExternalServiceException,
)
from .schemas import (
    ApiResponse,
    PaginatedResponse,
    PaginationMeta,
    ErrorDetail,
)
from .base import Repository
from .utils import (
    auth_required,
    admin_only,
    rate_limit,
)

__all__ = [
    # Exceptions
    "PeritoException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "ResourceNotFoundException",
    "ConflictException",
    "ExternalServiceException",
    # Schemas (DTOs)
    "ApiResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "ErrorDetail",
    # Base classes
    "Repository",
    # Decorators
    "auth_required",
    "admin_only",
    "rate_limit",
]
