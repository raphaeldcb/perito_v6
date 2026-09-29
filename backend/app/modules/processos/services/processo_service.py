"""Service layer for Processo business logic."""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.processo import Processo
from app.shared.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    ConflictException,
)
from app.modules.processos.repositories import ProcessoRepository
from app.modules.processos.schemas import (
    ProcessoCreateSchema,
    ProcessoUpdateSchema,
    ProcessoResponseSchema,
)


class ProcessoService:
    """Service for Processo business logic and validation."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = ProcessoRepository(db)

    async def create_processo(
        self,
        data: ProcessoCreateSchema,
    ) -> ProcessoResponseSchema:
        """Create a new processo with validation."""
        # Validate unique CNJ number
        existing = await self.repository.get_by_numero_cnj(data.numero_cnj)
        if existing:
            raise ConflictException(
                error_code="PROCESSO_DUPLICATE",
                detail=f"Processo with CNJ number {data.numero_cnj} already exists"
            )

        # Create new processo
        novo_processo = Processo(
            numero_cnj=data.numero_cnj,
            titulo=data.titulo,
            descricao=data.descricao,
            autor=data.autor,
            reu=data.reu,
            especialidade=data.especialidade,
            vara=data.vara,
            tribunal=data.tribunal,
            juiz=data.juiz,
            comarca=data.comarca,
            tipo_pericia=data.tipo_pericia,
            setor=data.setor,
            status=data.status,
            prioridade=data.prioridade,
            honorarios=data.honorarios,
            forma_recebimento=data.forma_recebimento,
            pago=data.pago,
            prazo=data.prazo,
            responsavel_id=data.responsavel_id,
            partes=data.partes or [],
            laboratorio=data.laboratorio,
            deslocamento=data.deslocamento,
            documentos=data.documentos or [],
            decisao_oficial_path=data.decisao_oficial_path,
        )

        created = await self.repository.create(novo_processo)
        return ProcessoResponseSchema.model_validate(created)

    async def get_processo(self, id: int) -> ProcessoResponseSchema:
        """Get processo by ID with validation."""
        processo = await self.repository.get_by_id(id)
        if not processo:
            raise ResourceNotFoundException(
                error_code="PROCESSO_NOT_FOUND",
                detail=f"Processo with ID {id} not found"
            )
        return ProcessoResponseSchema.model_validate(processo)

    async def update_processo(
        self,
        id: int,
        data: ProcessoUpdateSchema,
    ) -> ProcessoResponseSchema:
        """Update processo with validation."""
        # Check if processo exists
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise ResourceNotFoundException(
                error_code="PROCESSO_NOT_FOUND",
                detail=f"Processo with ID {id} not found"
            )

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(existing, key, value)

        self.db.commit()
        self.db.refresh(existing)
        return ProcessoResponseSchema.model_validate(existing)

    async def delete_processo(self, id: int) -> bool:
        """Delete processo (hard delete)."""
        return await self.repository.delete(id)

    async def list_processos(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """List all processos with pagination."""
        processos, total = await self.repository.list_with_filters(skip=skip, limit=limit)
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def list_by_comarca(
        self,
        comarca: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """List processos filtered by comarca."""
        if not comarca:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="comarca is required"
            )

        processos, total = await self.repository.list_by_comarca(
            comarca=comarca,
            skip=skip,
            limit=limit,
        )
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def list_by_vara(
        self,
        vara: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """List processos filtered by vara."""
        if not vara:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="vara is required"
            )

        processos, total = await self.repository.list_with_filters(
            vara=vara,
            skip=skip,
            limit=limit,
        )
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def list_by_area(
        self,
        area: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """List processos filtered by area (setor)."""
        if not area:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="area is required"
            )

        processos, total = await self.repository.list_with_filters(
            area=area,
            skip=skip,
            limit=limit,
        )
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def list_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """List processos filtered by status."""
        if not status:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="status is required"
            )

        processos, total = await self.repository.list_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def list_with_filters(
        self,
        skip: int = 0,
        limit: int = 50,
        comarca: Optional[str] = None,
        vara: Optional[str] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        responsavel_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """List processos with multiple filters."""
        processos, total = await self.repository.list_with_filters(
            skip=skip,
            limit=limit,
            comarca=comarca,
            vara=vara,
            area=area,
            status=status,
            responsavel_id=responsavel_id,
            search=search,
        )
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def search_processos(
        self,
        query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProcessoResponseSchema], int]:
        """Search processos by text query."""
        if not query or len(query) < 2:
            raise ValidationException(
                error_code="VALIDATION_ERROR",
                detail="Search query must be at least 2 characters"
            )

        processos, total = await self.repository.list_with_filters(
            skip=skip,
            limit=limit,
            search=query,
        )
        return (
            [ProcessoResponseSchema.model_validate(p) for p in processos],
            total,
        )

    async def get_distinct_comarcas(self) -> List[str]:
        """Get list of distinct comarcas."""
        return await self.repository.get_distinct_valores("comarca")

    async def get_distinct_varas(self) -> List[str]:
        """Get list of distinct varas."""
        return await self.repository.get_distinct_valores("vara")

    async def get_distinct_setores(self) -> List[str]:
        """Get list of distinct setores (areas)."""
        return await self.repository.get_distinct_valores("setor")

    async def get_distinct_statuses(self) -> List[str]:
        """Get list of distinct statuses."""
        return await self.repository.get_distinct_valores("status")

    async def get_stats(self) -> dict:
        """Get processo statistics."""
        total = await self.repository.count()

        return {
            "total_processos": total,
            "por_status": {
                "ativo": await self.repository.count_by_status("ativo"),
                "protocolado": await self.repository.count_by_status("protocolado"),
                "em_andamento": await self.repository.count_by_status("EM_ANDAMENTO"),
                "arquivado": await self.repository.count_by_status("Arquivado"),
                "concluido": await self.repository.count_by_status("Concluído"),
                "cancelado": await self.repository.count_by_status("Cancelado"),
            },
        }
