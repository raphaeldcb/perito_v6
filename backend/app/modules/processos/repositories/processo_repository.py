"""Repository for Processo model."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.processo import Processo
from app.shared import Repository
from app.shared.exceptions import ResourceNotFoundException


class ProcessoRepository(Repository[Processo]):
    """Repository for Processo CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    async def create(self, obj: Processo) -> Processo:
        """Create a new processo."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    async def get_by_id(self, id: int) -> Optional[Processo]:
        """Get processo by ID."""
        return self.db.query(Processo).filter(Processo.id == id).first()

    async def get_by_numero_cnj(self, numero_cnj: str) -> Optional[Processo]:
        """Get processo by CNJ number."""
        return self.db.query(Processo).filter(Processo.numero_cnj == numero_cnj).first()

    async def update(self, id: int, obj: Processo) -> Optional[Processo]:
        """Update a processo."""
        existing = await self.get_by_id(id)
        if not existing:
            raise ResourceNotFoundException(
                error_code="PROCESSO_NOT_FOUND",
                detail=f"Processo with ID {id} not found"
            )

        # Update only provided fields
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                setattr(existing, key, value)

        self.db.commit()
        self.db.refresh(existing)
        return existing

    async def delete(self, id: int) -> bool:
        """Delete a processo."""
        existing = await self.get_by_id(id)
        if not existing:
            raise ResourceNotFoundException(
                error_code="PROCESSO_NOT_FOUND",
                detail=f"Processo with ID {id} not found"
            )

        self.db.delete(existing)
        self.db.commit()
        return True

    async def list(self, skip: int = 0, limit: int = 100) -> List[Processo]:
        """List processos with pagination."""
        return self.db.query(Processo).offset(skip).limit(limit).all()

    async def list_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        comarca: Optional[str] = None,
        vara: Optional[str] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        responsavel_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Processo], int]:
        """List processos with advanced filtering.

        Returns tuple of (processos_list, total_count)
        """
        query = self.db.query(Processo)

        # Apply filters
        filters = []

        if comarca:
            filters.append(Processo.comarca == comarca)
        if vara:
            filters.append(Processo.vara == vara)
        if area:
            filters.append(Processo.setor == area)
        if status:
            filters.append(Processo.status == status)
        if responsavel_id:
            filters.append(Processo.responsavel_id == responsavel_id)

        # Text search
        if search:
            search_term = f"%{search}%"
            filters.append(
                (Processo.numero_cnj.ilike(search_term)) |
                (Processo.titulo.ilike(search_term)) |
                (Processo.autor.ilike(search_term)) |
                (Processo.reu.ilike(search_term))
            )

        if filters:
            query = query.filter(and_(*filters))

        total = query.count()
        processos = query.order_by(Processo.id.desc()).offset(skip).limit(limit).all()

        return processos, total

    async def count(self) -> int:
        """Count total processos."""
        return self.db.query(Processo).count()

    async def count_by_status(self, status: str) -> int:
        """Count processos by status."""
        return self.db.query(Processo).filter(Processo.status == status).count()

    async def count_by_comarca(self, comarca: str) -> int:
        """Count processos by comarca."""
        return self.db.query(Processo).filter(Processo.comarca == comarca).count()

    async def list_by_responsavel(
        self,
        responsavel_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Processo], int]:
        """List processos for a specific responsavel."""
        query = self.db.query(Processo).filter(Processo.responsavel_id == responsavel_id)
        total = query.count()
        processos = query.order_by(Processo.id.desc()).offset(skip).limit(limit).all()
        return processos, total

    async def list_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Processo], int]:
        """List processos by status."""
        query = self.db.query(Processo).filter(Processo.status == status)
        total = query.count()
        processos = query.order_by(Processo.id.desc()).offset(skip).limit(limit).all()
        return processos, total

    async def list_by_comarca(
        self,
        comarca: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Processo], int]:
        """List processos by comarca."""
        query = self.db.query(Processo).filter(Processo.comarca == comarca)
        total = query.count()
        processos = query.order_by(Processo.id.desc()).offset(skip).limit(limit).all()
        return processos, total

    async def get_distinct_valores(self, field: str) -> List[str]:
        """Get distinct values for a field (comarca, vara, setor, status)."""
        if field == "comarca":
            return [v[0] for v in self.db.query(Processo.comarca).distinct().all() if v[0]]
        elif field == "vara":
            return [v[0] for v in self.db.query(Processo.vara).distinct().all() if v[0]]
        elif field == "setor":
            return [v[0] for v in self.db.query(Processo.setor).distinct().all() if v[0]]
        elif field == "status":
            return [v[0] for v in self.db.query(Processo.status).distinct().all() if v[0]]
        else:
            return []
