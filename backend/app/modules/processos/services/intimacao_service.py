"""Service layer for Intimacao business logic."""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.kanban import Intimacao
from app.shared.exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from app.modules.processos.repositories import IntimacaoRepository
from app.modules.processos.schemas import (
    IntimacaoCreateSchema,
    IntimacaoUpdateSchema,
    IntimacaoResponseSchema,
)


class IntimacaoService:
    """Service for Intimacao business logic and validation."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = IntimacaoRepository(db)

    async def create_intimacao(
        self,
        data: IntimacaoCreateSchema,
    ) -> IntimacaoResponseSchema:
        """Create a new intimacao with validation."""
        # Validate required fields
        if not data.processo_id:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="processo_id is required"
            )

        if not data.origem:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="origem is required"
            )

        # Create new intimacao
        nova_intimacao = Intimacao(
            processo_id=data.processo_id,
            origem=data.origem,
            tipo=data.tipo,
            assunto=data.assunto,
            conteudo=data.conteudo,
            pdf_path=data.pdf_path,
            txt_path=data.txt_path,
            json_path=data.json_path,
            md_path=data.md_path,
            dados_estruturados=data.dados_estruturados,
            status=data.status,
            erros=data.erros,
            external_id=data.external_id,
            source_system=data.source_system,
        )

        created = await self.repository.create(nova_intimacao)
        return IntimacaoResponseSchema.model_validate(created)

    async def get_intimacao(self, id: int) -> IntimacaoResponseSchema:
        """Get intimacao by ID with validation."""
        intimacao = await self.repository.get_by_id(id)
        if not intimacao:
            raise ResourceNotFoundException(
                error_code="INTIMACAO_NOT_FOUND",
                detail=f"Intimacao with ID {id} not found"
            )
        return IntimacaoResponseSchema.model_validate(intimacao)

    async def update_intimacao(
        self,
        id: int,
        data: IntimacaoUpdateSchema,
    ) -> IntimacaoResponseSchema:
        """Update intimacao with validation."""
        # Check if intimacao exists
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise ResourceNotFoundException(
                error_code="INTIMACAO_NOT_FOUND",
                detail=f"Intimacao with ID {id} not found"
            )

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(existing, key, value)

        self.db.commit()
        self.db.refresh(existing)
        return IntimacaoResponseSchema.model_validate(existing)

    async def delete_intimacao(self, id: int) -> bool:
        """Delete intimacao (hard delete)."""
        return await self.repository.delete(id)

    async def list_intimacoes(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[IntimacaoResponseSchema], int]:
        """List all intimacoes with pagination."""
        intimacoes = await self.repository.list(skip=skip, limit=limit)
        total = await self.repository.count()
        return (
            [IntimacaoResponseSchema.model_validate(i) for i in intimacoes],
            total,
        )

    async def list_by_processo(
        self,
        processo_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[IntimacaoResponseSchema], int]:
        """List intimacoes for a specific processo."""
        if not processo_id:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="processo_id is required"
            )

        intimacoes, total = await self.repository.list_by_processo(
            processo_id=processo_id,
            skip=skip,
            limit=limit,
        )
        return (
            [IntimacaoResponseSchema.model_validate(i) for i in intimacoes],
            total,
        )

    async def list_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[IntimacaoResponseSchema], int]:
        """List intimacoes filtered by status."""
        if not status:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="status is required"
            )

        intimacoes, total = await self.repository.list_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )
        return (
            [IntimacaoResponseSchema.model_validate(i) for i in intimacoes],
            total,
        )

    async def list_with_filters(
        self,
        skip: int = 0,
        limit: int = 50,
        processo_id: Optional[int] = None,
        status: Optional[str] = None,
        origem: Optional[str] = None,
        tipo: Optional[str] = None,
    ) -> Tuple[List[IntimacaoResponseSchema], int]:
        """List intimacoes with multiple filters."""
        intimacoes, total = await self.repository.list_with_filters(
            skip=skip,
            limit=limit,
            processo_id=processo_id,
            status=status,
            origem=origem,
            tipo=tipo,
        )
        return (
            [IntimacaoResponseSchema.model_validate(i) for i in intimacoes],
            total,
        )

    async def count_pending_by_processo(self, processo_id: int) -> int:
        """Count pending intimacoes for a processo."""
        return await self.repository.count_pendentes_by_processo(processo_id)

    async def get_stats(self) -> dict:
        """Get intimacao statistics."""
        total = await self.repository.count()

        return {
            "total_intimacoes": total,
            "por_status": {
                "pendente": await self.repository.count_by_status("pendente"),
                "processada": await self.repository.count_by_status("processada"),
                "analisada": await self.repository.count_by_status("analisada"),
                "erro": await self.repository.count_by_status("erro"),
            },
        }
