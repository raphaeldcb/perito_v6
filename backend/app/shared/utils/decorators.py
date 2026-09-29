"""
Shared decorators for FastAPI route protection and utilities.

All decorators are implemented as FastAPI Depends wrappers for clean
dependency injection. No business logic — just contracts for authorization.
"""

import time
from functools import wraps
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any, TypeVar, Awaitable
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt  # type: ignore[import-untyped]

from app.shared.exceptions import (
    AuthenticationException,
    AuthorizationException,
)


# Mock user model for type hinting
class CurrentUser:
    """Represents the current authenticated user."""

    def __init__(
        self,
        id: int,
        username: str,
        email: str,
        roles: list[str],
    ) -> None:
        """Initialize CurrentUser with authentication details."""
        self.id: int = id
        self.username: str = username
        self.email: str = email
        self.roles: list[str] = roles


# Token configuration (should come from env/settings in production)
SECRET_KEY: str = "your-secret-key-change-in-production"
ALGORITHM: str = "HS256"


class RateLimitStore:
    """Simple in-memory rate limit store."""

    def __init__(self) -> None:
        """Initialize rate limit store."""
        self.requests: Dict[str, list[float]] = defaultdict(list)

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        """Check if a request is allowed based on rate limit."""
        now: float = time.time()
        # Clean old requests outside the window
        cutoff: float = now - window_seconds
        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]

        if len(self.requests[key]) >= max_requests:
            return False

        self.requests[key].append(now)
        return True


# Global rate limit store
_rate_limit_store: RateLimitStore = RateLimitStore()


async def get_current_user(request: Request) -> CurrentUser:
    """
    Dependency to extract and validate current user from JWT token.

    Raises:
        AuthenticationException: If token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise AuthenticationException(
            "Missing authorization header",
            context={"header": "Authorization"},
        )

    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise AuthenticationException(
                "Invalid authorization scheme",
                context={"scheme": scheme},
            )
    except ValueError:
        raise AuthenticationException(
            "Invalid authorization header format",
        )

    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        email: str = payload.get("email")
        roles: list[str] = payload.get("roles", [])

        if user_id is None:
            raise AuthenticationException("Invalid token payload")

        return CurrentUser(
            id=int(user_id),  # Convert string sub to int
            username=username,
            email=email,
            roles=roles,
        )
    except (JWTError, ValueError):
        raise AuthenticationException(
            "Invalid or expired token",
            context={"token_type": "bearer"},
        )


async def auth_required(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Decorator dependency for routes requiring authentication.

    Usage:
        @app.get("/protected")
        async def protected_route(user: CurrentUser = Depends(auth_required)):
            return {"user_id": user.id}

    Args:
        current_user: Current authenticated user from JWT token.

    Returns:
        The authenticated CurrentUser object.

    Raises:
        AuthenticationException: If user is not authenticated.
    """
    return current_user


async def admin_only(
    current_user: CurrentUser = Depends(auth_required),
) -> CurrentUser:
    """
    Decorator dependency for routes requiring admin role.

    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(user_id: int, admin: CurrentUser = Depends(admin_only)):
            return {"deleted": user_id}

    Args:
        current_user: Current authenticated user.

    Returns:
        The authenticated CurrentUser object if admin.

    Raises:
        AuthenticationException: If user is not authenticated.
        AuthorizationException: If user lacks admin role.
    """
    if "admin" not in current_user.roles:
        raise AuthorizationException(
            "Admin role required",
            context={
                "required_role": "admin",
                "user_roles": current_user.roles,
                "user_id": current_user.id,
            },
        )
    return current_user


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
) -> Callable[[F], F]:
    """
    Decorator for rate limiting routes.

    By default, uses the client IP as the key. Can be customized with key_func.

    Usage:
        @app.get("/api/search")
        @rate_limit(max_requests=10, window_seconds=60)
        async def search(q: str, request: Request):
            return {"results": []}

    Args:
        max_requests: Maximum number of requests allowed in the window.
        window_seconds: Time window in seconds.
        key_func: Optional function to extract a custom key from the request.
                 Defaults to client IP.

    Returns:
        Decorator function that wraps async route handlers.

    Raises:
        HTTPException: If rate limit is exceeded (429 Too Many Requests).
    """

    def default_key_func(request: Request) -> str:
        """Default: use client IP."""
        return request.client.host if request.client else "unknown"

    actual_key_func: Callable[[Request], str] = key_func or default_key_func

    def decorator(func: F) -> F:
        """Apply rate limiting to async function."""

        @wraps(func)
        async def wrapper(
            *args: Any,
            request: Optional[Request] = None,
            **kwargs: Any,
        ) -> Any:
            """Wrapper function that checks rate limits."""
            # Extract request from args if not in kwargs
            actual_request: Optional[Request] = request
            if actual_request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        actual_request = arg
                        break

            if actual_request is None:
                # If we can't find the request, skip rate limiting
                return await func(*args, **kwargs)

            key: str = actual_key_func(actual_request)
            if not _rate_limit_store.is_allowed(key, max_requests, window_seconds):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded: {max_requests} requests "
                        f"per {window_seconds}s"
                    ),
                )

            return await func(*args, request=actual_request, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


# Utility function for generating JWT tokens (for testing/auth module)
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode.
        expires_delta: Optional expiration time delta.

    Returns:
        Encoded JWT token string.
    """
    to_encode: Dict[str, Any] = data.copy()

    if expires_delta:
        expire: datetime = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt
