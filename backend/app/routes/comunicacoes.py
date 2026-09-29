"""Rotas para gestão de comunicações judiciais (emails monitorados)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models.comunicacoes import EmailMessage, JudicialStatus
from app.services.database import get_db

router = APIRouter(prefix="/api/v1/comunicacoes", tags=["comunicacoes"])


@router.get("")
def listar_comunicacoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    judicial: Optional[bool] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista comunicações (emails monitorados)."""
    query = db.query(EmailMessage).order_by(EmailMessage.received_datetime.desc())
    
    if judicial is not None:
        query = query.filter(EmailMessage.is_judicial == judicial)
    
    if status:
        query = query.filter(EmailMessage.status == status)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": e.id,
                "from_address": e.from_address,
                "from_name": e.from_name,
                "subject": e.subject,
                "received_datetime": e.received_datetime.isoformat(),
                "is_judicial": e.is_judicial,
                "status": e.status,
                "attachments_data": e.attachments_data,
                "has_attachments": e.has_attachments,
                "numero_processo": e.numero_processo
            }
            for e in items
        ]
    }


@router.get("/listar")
def listar_comunicacoes_compat(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    judicial: Optional[bool] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista comunicações (compatibilidade com frontend antigo)."""
    query = db.query(EmailMessage).order_by(EmailMessage.received_datetime.desc())

    if judicial is not None:
        query = query.filter(EmailMessage.is_judicial == judicial)

    if status:
        query = query.filter(EmailMessage.status == status)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "dados": [
            {
                "id": e.id,
                "from_address": e.from_address,
                "from_name": e.from_name,
                "subject": e.subject,
                "received_datetime": e.received_datetime.isoformat(),
                "is_judicial": e.is_judicial,
                "status": e.status,
                "attachments_data": e.attachments_data,
                "has_attachments": e.has_attachments,
                "numero_processo": e.numero_processo
            }
            for e in items
        ]
    }


@router.get("/painel/statistics")
def painel_statistics(db: Session = Depends(get_db)):
    """Retorna estatísticas do painel de comunicações."""
    total = db.query(EmailMessage).count()
    judicial = db.query(EmailMessage).filter(EmailMessage.is_judicial == True).count()
    nao_lidos = db.query(EmailMessage).filter(EmailMessage.status == "novo").count()

    return {
        "total_emails": total,
        "emails_judiciais": judicial,
        "emails_nao_processados": nao_lidos,
        "emails_processados": total - nao_lidos
    }


@router.get("/{email_id}")
def obter_comunicacao(
    email_id: int,
    db: Session = Depends(get_db)
):
    """Obtém detalhe de uma comunicação."""
    email = db.query(EmailMessage).filter(EmailMessage.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Comunicação não encontrada")

    return {
        "id": email.id,
        "from_address": email.from_address,
        "from_name": email.from_name,
        "to_addresses": email.to_addresses,
        "cc_addresses": email.cc_addresses,
        "subject": email.subject,
        "body_text": email.body_text,
        "received_datetime": email.received_datetime.isoformat(),
        "is_judicial": email.is_judicial,
        "judicial_confidence": email.judicial_confidence,
        "tribunal": email.tribunal,
        "vara": email.vara,
        "comarca": email.comarca,
        "numero_processo": email.numero_processo,
        "pedido": email.pedido,
        "prazo": email.prazo,
        "status": email.status,
        "attachments_data": email.attachments_data,
        "has_attachments": email.has_attachments,
        "analyzed_at": email.analyzed_at.isoformat() if email.analyzed_at else None,
        "categories": email.categories,
        "created_at": email.created_at.isoformat(),
        "updated_at": email.updated_at.isoformat()
    }
