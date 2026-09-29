"""
Auth module — Modularized authentication and authorization.

Wave 1 Modularization: Public interface (schemas + router only).
Internal implementation (models, repositories, services) isolated.

Exports:
- Schemas: LoginRequest, TokenResponse, UserSchema, etc. (PUBLIC DTOs)
- Router: FastAPI APIRouter with BE-01 to BE-13 endpoints (PUBLIC)

Never import repositories, services, or models from this module directly.
All inter-module communication via app.shared DTOs and exceptions.

Note: Services (AuthService, get_auth_service) should be obtained via
dependency injection (FastAPI Depends), not imported directly.
"""

from .schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserSchema,
    UserCreateRequest,
    UserUpdateRequest,
    ChangePasswordRequest,
    RoleSchema,
    PermissionSchema,
    UserListResponse,
)
from .routes import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserSchema",
    "UserCreateRequest",
    "UserUpdateRequest",
    "ChangePasswordRequest",
    "RoleSchema",
    "PermissionSchema",
    "UserListResponse",
    # Routes (PUBLIC — FastAPI integration)
    "router",
]
