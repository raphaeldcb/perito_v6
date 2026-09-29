"""
Boleto repository — CRUD operations for Boleto model.

Provides data access layer for boleto management.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.financeiro.models import Boleto, BoletoStatus
from app.shared.base.repository import Repository
from datetime import date


class BoletoRepository(Repository[Boleto]):
    """Repository for Boleto CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    async def create(self, obj: Boleto) -> Boleto:
        """Create a new boleto."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    async def get_by_id(self, id: int) -> Optional[Boleto]:
        """Get boleto by ID."""
        return self.db.query(Boleto).filter(Boleto.id == id).first()

    async def get_by_numero(self, numero: str) -> Optional[Boleto]:
        """Get boleto by numero (unique)."""
        return self.db.query(Boleto).filter(
            Boleto.numero == numero,
            Boleto.ativo == True
        ).first()

    async def get_by_inter_id(self, inter_id: str) -> Optional[Boleto]:
        """Get boleto by Inter ID."""
        return self.db.query(Boleto).filter(
            Boleto.inter_id == inter_id,
            Boleto.ativo == True
        ).first()

    async def get_by_processo(self, processo_id: int, skip: int = 0, limit: int = 100) -> List[Boleto]:
        """Get all boletos for a processo."""
        return self.db.query(Boleto).filter(
            Boleto.processo_id == processo_id,
            Boleto.ativo == True
        ).offset(skip).limit(limit).all()

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Boleto]:
        """Get boletos by status."""
        return self.db.query(Boleto).filter(
            Boleto.status == status,
            Boleto.ativo == True
        ).offset(skip).limit(limit).all()

    async def get_vencidos(self, data_ref: date, skip: int = 0, limit: int = 100) -> List[Boleto]:
        """Get overdue boletos (vencimento < data_ref)."""
        return self.db.query(Boleto).filter(
            Boleto.vencimento < data_ref,
            Boleto.status.in_([BoletoStatus.CRIADO, BoletoStatus.EMITIDO]),
            Boleto.ativo == True
        ).offset(skip).limit(limit).all()

    async def update(self, id: int, obj: Boleto) -> Optional[Boleto]:
        """Update boleto."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None

        for key, value in obj.dict(exclude_unset=True).items():
            setattr(db_obj, key, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> bool:
        """Soft delete boleto."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False

        db_obj.ativo = False
        self.db.commit()
        return True

    async def list(self, skip: int = 0, limit: int = 100) -> List[Boleto]:
        """List all active boletos."""
        return self.db.query(Boleto).filter(
            Boleto.ativo == True
        ).offset(skip).limit(limit).all()

    async def count_by_processo(self, processo_id: int) -> int:
        """Count boletos for a processo."""
        return self.db.query(Boleto).filter(
            Boleto.processo_id == processo_id,
            Boleto.ativo == True
        ).count()

    async def sum_by_processo(self, processo_id: int) -> float:
        """Sum total value of boletos for a processo."""
        from sqlalchemy import func
        result = self.db.query(func.sum(Boleto.valor)).filter(
            Boleto.processo_id == processo_id,
            Boleto.ativo == True
        ).scalar()
        return float(result) if result else 0.0


__all__ = ["BoletoRepository"]
