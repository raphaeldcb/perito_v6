"""
Laudos service — Business logic for Laudo operations.

Handles status transitions, validation, and coordination with repositories.
Implements state machine: RASCUNHO → REVISION → ASSINADO → ARQUIVADO
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.modules.laudos.models import Laudo, LaudoStatusEnum, LaudoTipoEnum
from app.modules.laudos.repositories import LaudoRepository, LaudoTemplateRepository
from app.shared.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    ConflictException,
)


class LaudoService:
    """Business logic for Laudo operations."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repo = LaudoRepository(db)
        self.template_repo = LaudoTemplateRepository(db)

    def create_draft(
        self,
        numero: str,
        processo_id: int,
        tipo: LaudoTipoEnum,
        template_id: Optional[int] = None,
        conteudo: Optional[Dict[str, Any]] = None,
    ) -> Laudo:
        """
        Create new Laudo in RASCUNHO status.

        Args:
            numero: Unique laudo number
            processo_id: FK to processo
            tipo: JUDICIAL or EXTRAJUDICIAL
            template_id: Optional FK to template
            conteudo: Optional initial content (JSON)

        Returns:
            Created Laudo object

        Raises:
            ValidationException: If numero exists or processo invalid
        """
        # Validate numero uniqueness
        existing = self.repo.get_by_numero(numero)
        if existing:
            raise ValidationException(
                detail=f"Laudo número '{numero}' já existe.",
                error_code="LAUDO_NUMERO_DUPLICADO",
                context={"numero": numero},
            )

        # Validate template if provided
        if template_id:
            template = self.template_repo.get_by_id(template_id)
            if not template:
                raise ResourceNotFoundException(
                    detail=f"Template ID {template_id} não encontrado.",
                    error_code="TEMPLATE_NOT_FOUND",
                    context={"template_id": template_id},
                )

        # Create in RASCUNHO status
        laudo = self.repo.create(
            numero=numero,
            processo_id=processo_id,
            tipo=tipo,
            status=LaudoStatusEnum.RASCUNHO,
            template_id=template_id,
            conteudo=conteudo or {},
        )

        return laudo

    def update_content(
        self,
        laudo_id: int,
        conteudo: Dict[str, Any],
    ) -> Laudo:
        """
        Update Laudo content.

        Only allowed in RASCUNHO or REVISION status.

        Args:
            laudo_id: Laudo ID
            conteudo: New content dict

        Returns:
            Updated Laudo

        Raises:
            ResourceNotFoundException: If Laudo not found
            ConflictException: If not in editable status
        """
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        # Only allow editing in RASCUNHO or REVISION
        if laudo.status not in [LaudoStatusEnum.RASCUNHO, LaudoStatusEnum.REVISION]:
            raise ConflictException(
                detail=f"Laudo em status '{laudo.status}' não pode ser editado.",
                error_code="LAUDO_NOT_EDITABLE",
                context={"laudo_id": laudo_id, "status": laudo.status},
            )

        updated = self.repo.update(
            laudo_id,
            conteudo=conteudo,
        )

        return updated

    def transition_status(
        self,
        laudo_id: int,
        new_status: LaudoStatusEnum,
        motivo: Optional[str] = None,
    ) -> Laudo:
        """
        Transition Laudo status (state machine).

        Valid transitions:
        - RASCUNHO → REVISION
        - REVISION → ASSINADO
        - ASSINADO → ARQUIVADO
        - Any → RASCUNHO (rollback)

        Args:
            laudo_id: Laudo ID
            new_status: Target status
            motivo: Optional reason

        Returns:
            Updated Laudo

        Raises:
            ResourceNotFoundException: If not found
            ConflictException: If invalid transition
        """
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        current_status = laudo.status

        # Validate transition
        valid_transitions = {
            LaudoStatusEnum.RASCUNHO: [LaudoStatusEnum.REVISION],
            LaudoStatusEnum.REVISION: [LaudoStatusEnum.ASSINADO, LaudoStatusEnum.RASCUNHO],
            LaudoStatusEnum.ASSINADO: [LaudoStatusEnum.ARQUIVADO, LaudoStatusEnum.RASCUNHO],
            LaudoStatusEnum.ARQUIVADO: [LaudoStatusEnum.RASCUNHO],  # Rare rollback
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise ConflictException(
                detail=f"Transição inválida: {current_status} → {new_status}",
                error_code="INVALID_STATUS_TRANSITION",
                context={
                    "current_status": current_status,
                    "requested_status": new_status,
                    "valid_targets": valid_transitions.get(current_status, []),
                },
            )

        # Apply transition
        update_data = {"status": new_status}

        # Set emission timestamp on ASSINADO
        if new_status == LaudoStatusEnum.ASSINADO and not laudo.data_emissao:
            update_data["data_emissao"] = datetime.utcnow()

        updated = self.repo.update(laudo_id, **update_data)

        return updated

    def assign_signature(
        self,
        laudo_id: int,
        assinante_id: int,
    ) -> Laudo:
        """
        Assign signature to Laudo.

        Sets assinante_id and data_assinatura. Usually called when transitioning to ASSINADO.

        Args:
            laudo_id: Laudo ID
            assinante_id: FK to usuario (signer)

        Returns:
            Updated Laudo
        """
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        updated = self.repo.update(
            laudo_id,
            assinante_id=assinante_id,
            data_assinatura=datetime.utcnow(),
        )

        return updated

    def get_laudo(self, laudo_id: int) -> Laudo:
        """Get Laudo by ID."""
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )
        return laudo

    def list_by_processo(
        self,
        processo_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple:
        """List laudos for a processo."""
        return self.repo.list_by_processo(processo_id, skip, limit)

    def list_by_status(
        self,
        status: LaudoStatusEnum,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple:
        """List laudos by status."""
        return self.repo.list_by_status(status, skip, limit)

    def soft_delete(self, laudo_id: int, deletado_por_id: int) -> Laudo:
        """Soft delete (mark deleted) Laudo."""
        laudo = self.repo.get_by_id(laudo_id)
        if not laudo:
            raise ResourceNotFoundException(
                detail=f"Laudo ID {laudo_id} não encontrado.",
                error_code="LAUDO_NOT_FOUND",
                context={"laudo_id": laudo_id},
            )

        return self.repo.soft_delete(laudo_id, deletado_por_id)
