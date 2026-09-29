"""
User repository for CRUD operations.
No cross-module imports — uses User model from app.models only.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import User
from app.shared import Repository
from app.services import hash_password
from app.shared.exceptions import (
    ResourceNotFoundException,
    ConflictException,
    ValidationException,
)


class UserRepository(Repository[User]):
    """User repository for database operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    async def create(self, user: User) -> User:
        """Create a new user."""
        # Check for duplicate email
        existing = self.db.query(User).filter(
            func.lower(User.email) == func.lower(user.email)
        ).first()

        if existing:
            raise ConflictException(
                detail=f"User with email {user.email} already exists",
                context={"email": user.email}
            )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    async def get_by_id(self, id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == id).first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        return self.db.query(User).filter(
            func.lower(User.email) == func.lower(email)
        ).first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (part before @)."""
        return self.db.query(User).filter(
            func.lower(User.email).like(f"{func.lower(username)}@%")
        ).first()

    async def update(self, id: int, user_data: dict) -> Optional[User]:
        """Update user by ID."""
        user = await self.get_by_id(id)
        if not user:
            raise ResourceNotFoundException(
                detail=f"User with ID {id} not found",
                context={"user_id": id}
            )

        # Prevent email change to duplicate
        if "email" in user_data and user_data["email"] != user.email:
            existing = await self.get_by_email(user_data["email"])
            if existing:
                raise ConflictException(
                    detail=f"Email {user_data['email']} already in use",
                    context={"email": user_data["email"]}
                )

        for key, value in user_data.items():
            if value is not None:
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    async def delete(self, id: int) -> bool:
        """Soft delete user (set is_active to False)."""
        user = await self.get_by_id(id)
        if not user:
            raise ResourceNotFoundException(
                detail=f"User with ID {id} not found",
                context={"user_id": id}
            )

        user.is_active = False
        self.db.commit()
        return True

    async def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List active users with pagination."""
        return self.db.query(User).filter(
            User.is_active == True
        ).offset(skip).limit(limit).all()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users (including inactive) with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    async def count_active(self) -> int:
        """Count active users."""
        return self.db.query(User).filter(User.is_active == True).count()

    async def count_all(self) -> int:
        """Count all users."""
        return self.db.query(User).count()

    async def count_by_role(self, role_id: int) -> int:
        """Count users by role."""
        return self.db.query(User).filter(User.role_id == role_id).count()

    async def list_by_role(self, role_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """List users by role."""
        return self.db.query(User).filter(
            User.role_id == role_id,
            User.is_active == True
        ).offset(skip).limit(limit).all()

    async def list_by_area(self, area: str, skip: int = 0, limit: int = 100) -> List[User]:
        """List users by area/specialty."""
        return self.db.query(User).filter(
            User.area == area,
            User.is_active == True
        ).offset(skip).limit(limit).all()

    async def update_password(self, id: int, hashed_password: str) -> bool:
        """Update user password."""
        user = await self.get_by_id(id)
        if not user:
            raise ResourceNotFoundException(
                detail=f"User with ID {id} not found",
                context={"user_id": id}
            )

        user.hashed_password = hashed_password
        self.db.commit()
        return True

    async def activate_user(self, id: int) -> bool:
        """Activate user."""
        user = await self.get_by_id(id)
        if not user:
            raise ResourceNotFoundException(
                detail=f"User with ID {id} not found",
                context={"user_id": id}
            )

        user.is_active = True
        self.db.commit()
        return True

    async def deactivate_user(self, id: int) -> bool:
        """Deactivate user."""
        return await self.delete(id)
