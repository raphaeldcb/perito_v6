from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.services import get_db
from app.middleware import get_current_user
from app.models import User, Delegacao
from app.schemas.delegacao import DelegacaoCreate, DelegacaoRead, DelegacaoAceitar, DelegacaoRecusar
from app.services.delegacao_service import enviar_email_delegacao, enviar_email_resposta_delegacao
from app.services.soft_delete import soft_delete
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/delegacao", tags=["delegacao"])


@router.post("", response_model=DelegacaoRead)
async def criar_delegacao(
    delegacao_data: DelegacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria nova delegação (analista → prestador)."""
    if delegacao_data.analista_id != current_user.id and current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado")

    prestador = db.query(User).filter(User.id == delegacao_data.prestador_id).first()
    if not prestador:
        raise HTTPException(status_code=404, detail="Prestador não encontrado")

    delegacao = Delegacao(
        tipo=delegacao_data.tipo,
        analista_id=delegacao_data.analista_id,
        prestador_id=delegacao_data.prestador_id,
        processo_id=delegacao_data.processo_id,
        valor=delegacao_data.valor,
        prazo_dias=delegacao_data.prazo_dias,
        descricao=delegacao_data.descricao
    )
    db.add(delegacao)
    db.commit()
    db.refresh(delegacao)

    enviar_email_delegacao(db, delegacao)

    return delegacao


@router.get("", response_model=list[DelegacaoRead])
async def listar_delegacoes(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista delegações do usuário (como analista ou prestador)."""
    query = db.query(Delegacao).filter(Delegacao.ativo == True)

    if status_filter:
        query = query.filter(Delegacao.status == status_filter)

    # Filtro por papel
    query = query.filter(
        (Delegacao.analista_id == current_user.id) |
        (Delegacao.prestador_id == current_user.id)
    )

    return query.all()


@router.get("/{delegacao_id}", response_model=DelegacaoRead)
async def obter_delegacao(
    delegacao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de delegação específica."""
    delegacao = db.query(Delegacao).filter(
        Delegacao.id == delegacao_id,
        Delegacao.ativo == True
    ).first()

    if not delegacao:
        raise HTTPException(status_code=404, detail="Delegação não encontrada")

    if delegacao.analista_id != current_user.id and delegacao.prestador_id != current_user.id:
        if current_user.role.name != "admin":
            raise HTTPException(status_code=403, detail="Não autorizado")

    return delegacao


@router.post("/{delegacao_id}/aceitar", response_model=DelegacaoRead)
async def aceitar_delegacao(
    delegacao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Prestador aceita delegação."""
    delegacao = db.query(Delegacao).filter(Delegacao.id == delegacao_id).first()
    if not delegacao:
        raise HTTPException(status_code=404, detail="Delegação não encontrada")

    if delegacao.prestador_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o prestador pode aceitar")

    if delegacao.status != "pendente":
        raise HTTPException(status_code=400, detail="Delegação não está pendente")

    delegacao.status = "aceito"
    delegacao.data_aceito = datetime.utcnow()
    db.commit()
    db.refresh(delegacao)

    enviar_email_resposta_delegacao(db, delegacao, aceito=True)

    return delegacao


@router.post("/{delegacao_id}/recusar", response_model=DelegacaoRead)
async def recusar_delegacao(
    delegacao_id: int,
    recusa_data: DelegacaoRecusar,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Prestador recusa delegação com motivo."""
    delegacao = db.query(Delegacao).filter(Delegacao.id == delegacao_id).first()
    if not delegacao:
        raise HTTPException(status_code=404, detail="Delegação não encontrada")

    if delegacao.prestador_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o prestador pode recusar")

    if delegacao.status != "pendente":
        raise HTTPException(status_code=400, detail="Delegação não está pendente")

    delegacao.status = "recusado"
    delegacao.motivo_recusa = recusa_data.motivo_recusa
    db.commit()
    db.refresh(delegacao)

    enviar_email_resposta_delegacao(db, delegacao, aceito=False, motivo=recusa_data.motivo_recusa)

    return delegacao


@router.delete("/{delegacao_id}")
async def deletar_delegacao(
    delegacao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-delete de delegação (analista ou admin)."""
    delegacao = db.query(Delegacao).filter(Delegacao.id == delegacao_id).first()
    if not delegacao:
        raise HTTPException(status_code=404, detail="Delegação não encontrada")

    if delegacao.analista_id != current_user.id and current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado")

    soft_delete(db, delegacao, current_user.id)

    return {"message": "Delegação deletada"}
