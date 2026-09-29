"""
Shared API response DTOs for all modules.

Modules communicate via these standardized DTOs only.
No direct imports between modules — use these schemas as the interface.
"""

from typing import TypeVar, Generic, Optional, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Standard error detail structure."""

    error_code: str = Field(..., description="Machine-readable error code")
    detail: str = Field(..., description="Human-readable error message")
    context: Optional[dict[str, Any]] = Field(
        None, description="Additional error context"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response envelope for all endpoints.

    All modules must wrap responses in this DTO to ensure consistency.
    Provides success/error status, data, metadata, and timestamps.
    """

    success: bool = Field(
        ..., description="Whether the request succeeded (True) or failed (False)"
    )
    data: Optional[T] = Field(None, description="Response data (null if error)")
    error: Optional[ErrorDetail] = Field(None, description="Error details (null if success)")
    meta: Optional[dict[str, Any]] = Field(
        None, description="Metadata (pagination, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "Example"},
                "error": None,
                "meta": {"pagination": {"page": 1, "total": 10}},
                "timestamp": "2025-08-10T12:00:00Z",
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated API response.

    Use this for list endpoints with pagination.
    """

    success: bool = Field(
        ..., description="Whether the request succeeded"
    )
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [{"id": 1, "name": "Item 1"}],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_items": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_previous": False,
                },
                "timestamp": "2025-08-10T12:00:00Z",
            }
        }
