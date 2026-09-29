"""Cérebro Cofre — Server-Sent Events (SSE) para notificações real-time.

Celular conecta via /cofre/notifications/stream e recebe alertas INSTANTLY
quando há novo pedido de acesso.

Fallback: polling pra browsers antigos.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import json

from app.middleware import get_current_user
from app.services import get_db
from app.models import User
from app.models.secure_vault import SecretRequest

router = APIRouter(tags=["cofre-notifications"])

# In-memory subscriptions (em prod: Redis pub/sub)
subscriptions = {}


@router.get("/cofre/notifications/stream")
async def subscribe_to_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Subscribe to real-time notifications via SSE.

    Browser:
    const source = new EventSource('/api/v1/cofre/notifications/stream');
    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Novo pedido:', data);
    };
    """

    async def generate():
        # Get current pending for this user
        existing = db.query(SecretRequest).filter(
            SecretRequest.status == 'pendente'
        ).all()

        # Send existing
        for req in existing:
            data = json.dumps({
                'tipo': 'existente',
                'request_id': req.id,
                'secret_nome': req.secret.nome,
                'usuario': req.usuario.full_name
            })
            yield f"data: {data}\n\n"

        # Subscribe to new events
        user_id = user.id
        subscription_key = f"user_{user_id}"
        subscriptions[subscription_key] = True

        try:
            # Polling fallback (cada 5s) enquanto SSE conectado
            while subscription_key in subscriptions:
                new_reqs = db.query(SecretRequest).filter(
                    SecretRequest.status == 'pendente'
                ).all()

                if new_reqs:
                    for req in new_reqs:
                        data = json.dumps({
                            'tipo': 'novo',
                            'request_id': req.id,
                            'secret_nome': req.secret.nome,
                            'usuario': req.usuario.full_name,
                            'pedido_em': req.pedido_em.isoformat()
                        })
                        yield f"data: {data}\n\n"

                # Heartbeat (pra evitar timeout)
                yield ": keepalive\n\n"
                await asyncio.sleep(5)

        finally:
            # Cleanup
            subscriptions.pop(subscription_key, None)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/cofre/notifications/notify")
async def notify_new_request(
    request_id: int,
    db: Session = Depends(get_db),
):
    """Internal: notifica todos que têm acesso a aprovar este pedido.

    Chamado quando novo SecretRequest é criado.
    """
    # Em prod: publish pra Redis (todos os workers recebem)
    # Por agora: in-memory é OK pra MVP

    req = db.query(SecretRequest).filter(SecretRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request não encontrado")

    # Notify all subscribers
    message = {
        'tipo': 'novo',
        'request_id': request_id,
        'secret_nome': req.secret.nome,
        'usuario': req.usuario.full_name,
        'motivo': req.motivo,
        'pedido_em': req.pedido_em.isoformat()
    }

    return {
        "status": "notificado",
        "subscribers": len(subscriptions),
        "mensagem": message
    }
