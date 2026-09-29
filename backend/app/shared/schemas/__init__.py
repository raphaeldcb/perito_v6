"""Shared DTOs for all modules."""

from .api_response import (
    ApiResponse,
    PaginatedResponse,
    PaginationMeta,
    ErrorDetail,
)

__all__ = [
    "ApiResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "ErrorDetail",
]
