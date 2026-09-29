from sqlalchemy.orm import Session
from datetime import datetime
from typing import Any


def soft_delete(db: Session, model_instance: Any, deleted_by_id: int) -> None:
    """
    Marca instância como deletada (soft-delete) em vez de deletar fisicamente.

    Args:
        db: Sessão SQLAlchemy
        model_instance: Instância do modelo a deletar
        deleted_by_id: ID do usuário que está deletando
    """
    if hasattr(model_instance, 'ativo'):
        model_instance.ativo = False

    if hasattr(model_instance, 'deletado_por_id'):
        model_instance.deletado_por_id = deleted_by_id

    if hasattr(model_instance, 'deletado_em'):
        model_instance.deletado_em = datetime.utcnow()

    db.commit()
