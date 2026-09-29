"""
Auth service (singleton) for authentication and authorization.
Handles JWT tokens, password hashing, permission validation.
"""

from typing import Optional, Dict, Any
from datetime import timedelta
from sqlalchemy.orm import Session

from app.models import User, Role, Permission
from app.services import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.shared.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
)
from app.modules.auth.repositories import UserRepository


class AuthService:
    """Authentication and authorization service (singleton)."""

    def __init__(self, db: Session):
        """Initialize auth service with database session."""
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate(
        self,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Authenticate user by email/username and password.

        Args:
            email: Email or username
            password: Plain password

        Returns:
            Dict with access_token, refresh_token, expires_in

        Raises:
            AuthenticationException: If credentials invalid or user inactive
        """
        # Try exact email match first
        user = await self.user_repo.get_by_email(email)

        # If not found and no @, try username match
        if not user and "@" not in email:
            user = await self.user_repo.get_by_username(email)

        if not user:
            raise AuthenticationException(
                detail="Invalid credentials",
                context={"email": email}
            )

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise AuthenticationException(
                detail="Invalid credentials",
                context={"email": email}
            )

        # Check if user is active
        if not user.is_active:
            raise AuthenticationException(
                detail="User account is inactive",
                context={"user_id": user.id}
            )

        # Generate tokens
        token_data = {"sub": str(user.id)}
        if user.role:
            token_data["role"] = user.role.name

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 15 * 60,  # 15 minutes
        }

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with new access_token, refresh_token, expires_in

        Raises:
            AuthenticationException: If refresh token invalid or user not found
        """
        payload = decode_token(refresh_token)

        if not payload:
            raise AuthenticationException(
                detail="Invalid refresh token"
            )

        if payload.get("type") != "refresh":
            raise AuthenticationException(
                detail="Invalid token type"
            )

        user_id = int(payload.get("sub"))
        user = await self.user_repo.get_by_id(user_id)

        if not user or not user.is_active:
            raise AuthenticationException(
                detail="User not found or inactive",
                context={"user_id": user_id}
            )

        # Generate new tokens
        token_data = {"sub": str(user.id)}
        if user.role:
            token_data["role"] = user.role.name

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 15 * 60,
        }

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current plain password
            new_password: New plain password

        Returns:
            True if successful

        Raises:
            AuthenticationException: If current password invalid
            ResourceNotFoundException: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise ResourceNotFoundException(
                detail=f"User {user_id} not found",
                context={"user_id": user_id}
            )

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationException(
                detail="Current password is incorrect",
                context={"user_id": user_id}
            )

        # Hash new password and update
        hashed_new = hash_password(new_password)
        return await self.user_repo.update_password(user_id, hashed_new)

    async def validate_permissions(
        self,
        user_id: int,
        action: str,
        resource: str
    ) -> bool:
        """
        Validate if user has permission to perform action on resource.

        Args:
            user_id: User ID
            action: Action (read, write, delete, etc.)
            resource: Resource (processes, users, etc.)

        Returns:
            True if user has permission

        Raises:
            AuthorizationException: If permission denied
        """
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise ResourceNotFoundException(
                detail=f"User {user_id} not found",
                context={"user_id": user_id}
            )

        # Load role with permissions
        role = self.db.query(Role).filter(Role.id == user.role_id).first()
        if not role:
            raise AuthorizationException(
                detail="User role not found",
                context={"user_id": user_id, "role_id": user.role_id}
            )

        # Check permissions
        permissions = self.db.query(Permission).filter(
            Permission.role_id == role.id
        ).all()

        # Admin has all permissions
        if role.name == "admin":
            return True

        # Check specific permission
        for perm in permissions:
            if (perm.action == action or perm.action == "*") and \
               (perm.resource == resource or perm.resource == "*"):
                return True

        raise AuthorizationException(
            detail=f"Permission denied: {action} on {resource}",
            context={"user_id": user_id, "action": action, "resource": resource}
        )

    async def get_user_permissions(self, user_id: int) -> list:
        """
        Get all permissions for user.

        Args:
            user_id: User ID

        Returns:
            List of permission dicts

        Raises:
            ResourceNotFoundException: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise ResourceNotFoundException(
                detail=f"User {user_id} not found",
                context={"user_id": user_id}
            )

        permissions = self.db.query(Permission).filter(
            Permission.role_id == user.role_id
        ).all()

        return [
            {
                "action": p.action,
                "resource": p.resource,
                "description": p.description
            }
            for p in permissions
        ]


# Global singleton instance
_auth_service_instance: Optional[AuthService] = None


def get_auth_service(db: Session) -> AuthService:
    """Get or create singleton auth service."""
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService(db)
    return _auth_service_instance
