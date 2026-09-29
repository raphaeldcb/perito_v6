"""
Auth module schemas (Pydantic models) for request/response DTOs.
All responses wrapped in ApiResponse (shared layer).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    """BE-01: Login request DTO."""

    email: str = Field(..., description="Email or username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Auth token response DTO."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Expiry in seconds")


class RefreshRequest(BaseModel):
    """BE-02: Refresh token request DTO."""

    refresh_token: str = Field(..., description="Refresh token")


class UserSchema(BaseModel):
    """User schema DTO."""

    id: int
    email: str
    full_name: str
    is_active: bool
    role_id: int
    area: Optional[str] = None
    nivel: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    """User creation request DTO (admin only)."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=255)
    role_id: int
    area: Optional[str] = None
    nivel: Optional[str] = None
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    """User update request DTO."""

    full_name: Optional[str] = None
    area: Optional[str] = None
    nivel: Optional[str] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """BE-04: Change password request DTO."""

    senha_atual: str = Field(..., description="Current password")
    nova_senha: str = Field(..., min_length=6, description="New password")


class RoleSchema(BaseModel):
    """Role schema DTO."""

    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class PermissionSchema(BaseModel):
    """Permission schema DTO."""

    id: int
    role_id: int
    action: str
    resource: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response DTO."""

    id: int
    email: str
    full_name: str
    is_active: bool
    role_id: int
    created_at: datetime

    class Config:
        from_attributes = True
