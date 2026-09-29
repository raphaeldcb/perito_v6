"""Base repository class for all modules."""

from typing import TypeVar, Generic, Optional, List
from abc import ABC, abstractmethod

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """
    Abstract base repository for all modules.

    Provides common data access patterns while allowing modules to
    implement their own specific queries and persistence logic.
    """

    @abstractmethod
    async def create(self, obj: T) -> T:
        """Create a new record."""
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get a record by ID."""
        pass

    @abstractmethod
    async def update(self, id: int, obj: T) -> Optional[T]:
        """Update an existing record."""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        pass

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List records with pagination."""
        pass
