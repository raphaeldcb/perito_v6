"""
Laudos repository — CRUD operations for Laudo and LaudoTemplate entities.

Interfaces with SQLAlchemy ORM and database layer.
No business logic — data access only.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.modules.laudos.models import Laudo, LaudoTemplate, LaudoStatusEnum
from app.shared.exceptions import ResourceNotFoundException


class LaudoRepository:
    """Repository for Laudo CRUD operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(self, **kwargs) -> Laudo:
        """Create new Laudo."""
        laudo = Laudo(**kwargs)
        self.db.add(laudo)
        self.db.commit()
        self.db.refresh(laudo)
        return laudo

    def get_by_id(self, laudo_id: int) -> Optional[Laudo]:
        """Get Laudo by ID (exclude soft deleted)."""
        return self.db.query(Laudo).filter(
            and_(Laudo.id == laudo_id, Laudo.deletado == False)
        ).first()

    def get_by_numero(self, numero: str) -> Optional[Laudo]:
        """Get Laudo by numero (unique)."""
        return self.db.query(Laudo).filter(
            and_(Laudo.numero == numero, Laudo.deletado == False)
        ).first()

    def list_by_processo(
        self,
        processo_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Laudo], int]:
        """List laudos for a processo with pagination."""
        query = self.db.query(Laudo).filter(
            and_(Laudo.processo_id == processo_id, Laudo.deletado == False)
        ).order_by(desc(Laudo.created_at))

        total = query.count()
        laudos = query.offset(skip).limit(limit).all()
        return laudos, total

    def list_by_status(
        self,
        status: LaudoStatusEnum,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Laudo], int]:
        """List laudos by status with pagination."""
        query = self.db.query(Laudo).filter(
            and_(Laudo.status == status, Laudo.deletado == False)
        ).order_by(desc(Laudo.created_at))

        total = query.count()
        laudos = query.offset(skip).limit(limit).all()
        return laudos, total

    def update(self, laudo_id: int, **kwargs) -> Optional[Laudo]:
        """Update Laudo fields."""
        laudo = self.get_by_id(laudo_id)
        if not laudo:
            return None

        for key, value in kwargs.items():
            if hasattr(laudo, key):
                setattr(laudo, key, value)

        self.db.commit()
        self.db.refresh(laudo)
        return laudo

    def soft_delete(self, laudo_id: int, deletado_por_id: int) -> Optional[Laudo]:
        """Soft delete Laudo (mark as deleted)."""
        laudo = self.get_by_id(laudo_id)
        if not laudo:
            return None

        laudo.deletado = True
        laudo.deletado_por_id = deletado_por_id
        from datetime import datetime
        laudo.deletado_em = datetime.utcnow()

        self.db.commit()
        self.db.refresh(laudo)
        return laudo

    def delete(self, laudo_id: int) -> bool:
        """Hard delete Laudo (permanent, use sparingly)."""
        laudo = self.db.query(Laudo).filter(Laudo.id == laudo_id).first()
        if not laudo:
            return False

        self.db.delete(laudo)
        self.db.commit()
        return True


class LaudoTemplateRepository:
    """Repository for LaudoTemplate CRUD operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(self, **kwargs) -> LaudoTemplate:
        """Create new LaudoTemplate."""
        template = LaudoTemplate(**kwargs)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_by_id(self, template_id: int) -> Optional[LaudoTemplate]:
        """Get template by ID."""
        return self.db.query(LaudoTemplate).filter(
            LaudoTemplate.id == template_id
        ).first()

    def get_by_nome(self, nome: str) -> Optional[LaudoTemplate]:
        """Get template by name (unique)."""
        return self.db.query(LaudoTemplate).filter(
            LaudoTemplate.nome == nome
        ).first()

    def list_active(self) -> List[LaudoTemplate]:
        """List all active templates."""
        return self.db.query(LaudoTemplate).filter(
            LaudoTemplate.ativo == True
        ).order_by(LaudoTemplate.nome).all()

    def list_all(self, skip: int = 0, limit: int = 100) -> tuple[List[LaudoTemplate], int]:
        """List all templates with pagination."""
        query = self.db.query(LaudoTemplate).order_by(LaudoTemplate.nome)
        total = query.count()
        templates = query.offset(skip).limit(limit).all()
        return templates, total

    def update(self, template_id: int, **kwargs) -> Optional[LaudoTemplate]:
        """Update template fields."""
        template = self.get_by_id(template_id)
        if not template:
            return None

        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template_id: int) -> bool:
        """Delete template."""
        template = self.db.query(LaudoTemplate).filter(
            LaudoTemplate.id == template_id
        ).first()
        if not template:
            return False

        self.db.delete(template)
        self.db.commit()
        return True
