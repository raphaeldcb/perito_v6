"""Repository for Intimacao model."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.kanban import Intimacao
from app.shared import Repository
from app.shared.exceptions import ResourceNotFoundException


class IntimacaoRepository(Repository[Intimacao]):
    """Repository for Intimacao CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    async def create(self, obj: Intimacao) -> Intimacao:
        """Create a new intimacao."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    async def get_by_id(self, id: int) -> Optional[Intimacao]:
        """Get intimacao by ID."""
        return self.db.query(Intimacao).filter(Intimacao.id == id).first()

    async def update(self, id: int, obj: Intimacao) -> Optional[Intimacao]:
        """Update an intimacao."""
        existing = await self.get_by_id(id)
        if not existing:
            raise ResourceNotFoundException(
                error_code="INTIMACAO_NOT_FOUND",
                detail=f"Intimacao with ID {id} not found"
            )

        # Update only provided fields
        for key, value in obj.__dict__.items():
            if not key.startswith("_") and value is not None:
                setattr(existing, key, value)

        self.db.commit()
        self.db.refresh(existing)
        return existing

    async def delete(self, id: int) -> bool:
        """Delete an intimacao."""
        existing = await self.get_by_id(id)
        if not existing:
            raise ResourceNotFoundException(
                error_code="INTIMACAO_NOT_FOUND",
                detail=f"Intimacao with ID {id} not found"
            )

        self.db.delete(existing)
        self.db.commit()
        return True

    async def list(self, skip: int = 0, limit: int = 100) -> List[Intimacao]:
        """List intimacoes with pagination."""
        return self.db.query(Intimacao).offset(skip).limit(limit).all()

    async def list_by_processo(
        self,
        processo_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Intimacao], int]:
        """List intimacoes for a specific processo."""
        query = self.db.query(Intimacao).filter(Intimacao.processo_id == processo_id)
        total = query.count()
        intimacoes = query.order_by(Intimacao.created_at.desc()).offset(skip).limit(limit).all()
        return intimacoes, total

    async def list_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Intimacao], int]:
        """List intimacoes by status."""
        query = self.db.query(Intimacao).filter(Intimacao.status == status)
        total = query.count()
        intimacoes = query.order_by(Intimacao.created_at.desc()).offset(skip).limit(limit).all()
        return intimacoes, total

    async def list_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        processo_id: Optional[int] = None,
        status: Optional[str] = None,
        origem: Optional[str] = None,
        tipo: Optional[str] = None,
    ) -> tuple[List[Intimacao], int]:
        """List intimacoes with advanced filtering."""
        query = self.db.query(Intimacao)

        filters = []
        if processo_id:
            filters.append(Intimacao.processo_id == processo_id)
        if status:
            filters.append(Intimacao.status == status)
        if origem:
            filters.append(Intimacao.origem == origem)
        if tipo:
            filters.append(Intimacao.tipo == tipo)

        if filters:
            query = query.filter(and_(*filters))

        total = query.count()
        intimacoes = query.order_by(Intimacao.created_at.desc()).offset(skip).limit(limit).all()
        return intimacoes, total

    async def count(self) -> int:
        """Count total intimacoes."""
        return self.db.query(Intimacao).count()

    async def count_by_status(self, status: str) -> int:
        """Count intimacoes by status."""
        return self.db.query(Intimacao).filter(Intimacao.status == status).count()

    async def count_by_processo(self, processo_id: int) -> int:
        """Count intimacoes for a specific processo."""
        return self.db.query(Intimacao).filter(Intimacao.processo_id == processo_id).count()

    async def count_pendentes_by_processo(self, processo_id: int) -> int:
        """Count pending intimacoes for a processo."""
        return self.db.query(Intimacao).filter(
            (Intimacao.processo_id == processo_id) &
            (Intimacao.status.in_(["pendente", "processando"]))
        ).count()

    async def get_by_external_id(
        self,
        external_id: str,
        source_system: str,
    ) -> Optional[Intimacao]:
        """Get intimacao by external ID and source system."""
        return self.db.query(Intimacao).filter(
            (Intimacao.external_id == external_id) &
            (Intimacao.source_system == source_system)
        ).first()
