"""
Auth module routes (modularized).
Endpoints: BE-01 to BE-13 (login, refresh, me, users CRUD, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.services import get_db
from app.middleware import get_current_user
from app.middleware.rate_limiting import limiter
from app.shared.schemas import ApiResponse
from app.models import User, Role
from app.services import hash_password, verify_password

from app.modules.auth.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserSchema,
    UserCreateRequest,
    UserUpdateRequest,
    ChangePasswordRequest,
    UserListResponse,
)
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import get_auth_service
from app.shared.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    ResourceNotFoundException,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================================
# BE-01: Login endpoint
# ============================================================================
@router.post("/login", response_model=ApiResponse[TokenResponse])
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    BE-01: User login endpoint.

    Accepts email or username. Rate limited to 5 attempts per minute.
    Returns: access_token, refresh_token, expires_in
    """
    try:
        auth_service = get_auth_service(db)
        token_data = await auth_service.authenticate(
            login_request.email,
            login_request.password
        )

        return ApiResponse(
            success=True,
            data=TokenResponse(**token_data),
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except AuthenticationException as e:
        return ApiResponse(
            success=False,
            data=None,
            error={"error_code": e.error_code, "detail": e.detail},
            timestamp=__import__("datetime").datetime.utcnow()
        )


# ============================================================================
# BE-02: Refresh token endpoint
# ============================================================================
@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    BE-02: Refresh access token endpoint.

    Returns new access_token and refresh_token.
    """
    try:
        auth_service = get_auth_service(db)
        token_data = await auth_service.refresh_access_token(
            refresh_request.refresh_token
        )

        return ApiResponse(
            success=True,
            data=TokenResponse(**token_data),
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except AuthenticationException as e:
        return ApiResponse(
            success=False,
            data=None,
            error={"error_code": e.error_code, "detail": e.detail},
            timestamp=__import__("datetime").datetime.utcnow()
        )


# ============================================================================
# BE-03: Get current user endpoint
# ============================================================================
@router.get("/me", response_model=ApiResponse[UserSchema])
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-03: Get current authenticated user info.
    """
    # Refresh user from DB to get latest role info
    user = db.query(User).filter(User.id == current_user.id).first()

    if not user:
        raise ResourceNotFoundException(
            detail="User not found"
        )

    return ApiResponse(
        success=True,
        data=UserSchema(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role_id=user.role_id,
            area=user.area,
            nivel=user.nivel,
            created_at=user.created_at,
            updated_at=user.updated_at
        ),
        timestamp=__import__("datetime").datetime.utcnow()
    )


# ============================================================================
# BE-04: Change password endpoint
# ============================================================================
@router.post("/change-password", response_model=ApiResponse[dict])
async def change_password(
    change_pwd: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-04: Change password for authenticated user.
    """
    try:
        # Validate new password length
        if len(change_pwd.nova_senha) < 6:
            raise ValidationException(
                detail="New password must be at least 6 characters"
            )

        auth_service = get_auth_service(db)
        await auth_service.change_password(
            current_user.id,
            change_pwd.senha_atual,
            change_pwd.nova_senha
        )

        return ApiResponse(
            success=True,
            data={"message": "Password changed successfully"},
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except (AuthenticationException, ValidationException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )


# ============================================================================
# BE-05: Logout endpoint
# ============================================================================
@router.post("/logout", response_model=ApiResponse[dict])
async def logout(current_user: User = Depends(get_current_user)):
    """
    BE-05: Logout endpoint (stateless — just confirms client discards token).
    """
    return ApiResponse(
        success=True,
        data={"message": "Logged out successfully"},
        timestamp=__import__("datetime").datetime.utcnow()
    )


# ============================================================================
# BE-06: List users (admin only)
# ============================================================================
@router.get("/users", response_model=ApiResponse[list])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-06: List all users (admin only).
    """
    # Check admin permission
    if current_user.role_id != 1:  # Assuming 1 is admin
        raise AuthorizationException(
            detail="Only admins can list users"
        )

    repo = UserRepository(db)
    users = await repo.list_all(skip=skip, limit=limit)

    user_dicts = [
        UserListResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            role_id=u.role_id,
            created_at=u.created_at
        )
        for u in users
    ]

    return ApiResponse(
        success=True,
        data=[u.model_dump() for u in user_dicts],
        timestamp=__import__("datetime").datetime.utcnow()
    )


# ============================================================================
# BE-07: Get user by ID (admin only)
# ============================================================================
@router.get("/users/{user_id}", response_model=ApiResponse[UserSchema])
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-07: Get user by ID (admin only).
    """
    # Check admin permission
    if current_user.role_id != 1:
        raise AuthorizationException(
            detail="Only admins can view users"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise ResourceNotFoundException(
            detail=f"User {user_id} not found"
        )

    return ApiResponse(
        success=True,
        data=UserSchema(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role_id=user.role_id,
            area=user.area,
            nivel=user.nivel,
            created_at=user.created_at,
            updated_at=user.updated_at
        ),
        timestamp=__import__("datetime").datetime.utcnow()
    )


# ============================================================================
# BE-08: Create user (admin only)
# ============================================================================
@router.post("/users", response_model=ApiResponse[UserSchema])
async def create_user(
    user_create: UserCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-08: Create new user (admin only).
    """
    # Check admin permission
    if current_user.role_id != 1:
        raise AuthorizationException(
            detail="Only admins can create users"
        )

    try:
        repo = UserRepository(db)

        new_user = User(
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hash_password(user_create.password),
            role_id=user_create.role_id,
            area=user_create.area,
            nivel=user_create.nivel,
            is_active=user_create.is_active
        )

        created_user = await repo.create(new_user)

        return ApiResponse(
            success=True,
            data=UserSchema(
                id=created_user.id,
                email=created_user.email,
                full_name=created_user.full_name,
                is_active=created_user.is_active,
                role_id=created_user.role_id,
                area=created_user.area,
                nivel=created_user.nivel,
                created_at=created_user.created_at,
                updated_at=created_user.updated_at
            ),
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ============================================================================
# BE-09: Update user (admin only)
# ============================================================================
@router.patch("/users/{user_id}", response_model=ApiResponse[UserSchema])
async def update_user(
    user_id: int,
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-09: Update user (admin only).
    """
    # Check admin permission
    if current_user.role_id != 1:
        raise AuthorizationException(
            detail="Only admins can update users"
        )

    try:
        repo = UserRepository(db)

        update_data = {
            k: v for k, v in user_update.model_dump().items()
            if v is not None
        }

        updated_user = await repo.update(user_id, update_data)

        return ApiResponse(
            success=True,
            data=UserSchema(
                id=updated_user.id,
                email=updated_user.email,
                full_name=updated_user.full_name,
                is_active=updated_user.is_active,
                role_id=updated_user.role_id,
                area=updated_user.area,
                nivel=updated_user.nivel,
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at
            ),
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=e.detail
        )


# ============================================================================
# BE-10: Delete user (admin only) — soft delete
# ============================================================================
@router.delete("/users/{user_id}", response_model=ApiResponse[dict])
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-10: Delete user (soft delete, admin only).
    """
    # Check admin permission
    if current_user.role_id != 1:
        raise AuthorizationException(
            detail="Only admins can delete users"
        )

    try:
        repo = UserRepository(db)
        await repo.delete(user_id)

        return ApiResponse(
            success=True,
            data={"message": f"User {user_id} deleted"},
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=e.detail
        )


# ============================================================================
# BE-11: Activate user (admin only)
# ============================================================================
@router.post("/users/{user_id}/activate", response_model=ApiResponse[dict])
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-11: Activate user (admin only).
    """
    if current_user.role_id != 1:
        raise AuthorizationException(
            detail="Only admins can activate users"
        )

    try:
        repo = UserRepository(db)
        await repo.activate_user(user_id)

        return ApiResponse(
            success=True,
            data={"message": f"User {user_id} activated"},
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=e.detail
        )


# ============================================================================
# BE-12: Deactivate user (admin only)
# ============================================================================
@router.post("/users/{user_id}/deactivate", response_model=ApiResponse[dict])
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-12: Deactivate user (admin only).
    """
    if current_user.role_id != 1:
        raise AuthorizationException(
            detail="Only admins can deactivate users"
        )

    try:
        repo = UserRepository(db)
        await repo.deactivate_user(user_id)

        return ApiResponse(
            success=True,
            data={"message": f"User {user_id} deactivated"},
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=e.detail
        )


# ============================================================================
# BE-13: User permissions (get user's permissions)
# ============================================================================
@router.get("/users/{user_id}/permissions", response_model=ApiResponse[list])
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    BE-13: Get user's permissions.
    Users can view their own permissions; admins can view any.
    """
    # Users can only view their own permissions
    if current_user.id != user_id and current_user.role_id != 1:
        raise AuthorizationException(
            detail="Cannot view other users' permissions"
        )

    try:
        auth_service = get_auth_service(db)
        permissions = await auth_service.get_user_permissions(user_id)

        return ApiResponse(
            success=True,
            data=permissions,
            timestamp=__import__("datetime").datetime.utcnow()
        )
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=e.detail
        )
