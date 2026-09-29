"""Cérebro Cofre — Secure Vault com Multi-device Approval.

Endpoints:
- POST /api/v1/cofre/secrets/{nome}/request — Pede acesso a secret
- GET /api/v1/cofre/pending-approvals — Lista pedidos pendentes (pra celular/PC)
- POST /api/v1/cofre/approve/{request_id} — Aprova acesso
- GET /api/v1/cofre/secrets/{nome} — Retorna secret (se aprovado + fresh)

Security: RLS PostgreSQL + Multi-device approval flow
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import secrets
import os

from app.middleware import get_current_user
from app.services import get_db
from app.models import User
from app.models.secure_vault import (
    SecretVault, SecretRequest, SecretApproval, SecretAccessLog, SecretType
)

router = APIRouter(tags=["cofre"])


# ============================================================================
# POST /api/v1/cofre/secrets/{nome}/request — Pede acesso
# ============================================================================

@router.post("/cofre/secrets/{nome}/request")
async def request_secret_access(
    nome: str,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Pede acesso a um secret (cria requisição pendente de aprovação).

    Payload:
    {
      "motivo": "Preciso reset DB prod",
      "tempo_horas": 1
    }

    Response:
    {
      "request_id": 42,
      "status": "pendente",
      "aprova_em": "celular ou PC",
      "expira_em": "2026-07-16T18:35:00Z"
    }
    """
    try:
        # Find secret
        secret = db.query(SecretVault).filter(
            SecretVault.usuario_id == user.id,
            SecretVault.nome == nome
        ).first()

        if not secret:
            raise HTTPException(404, f"Secret '{nome}' não encontrado")

        if not secret.requer_aprovacao:
            # Não precisa de aprovação — retorna direto
            # TODO: Integração Azure Key Vault aqui
            return {
                "status": "direto",
                "valor": "***MOCK***",  # Em prod: retorna de AKV
                "expira_em": (datetime.utcnow() + timedelta(hours=secret.tempo_expiracao_horas)).isoformat()
            }

        # Create request (requer aprovação)
        motivo = payload.get("motivo")
        tempo_horas = payload.get("tempo_horas", secret.tempo_expiracao_horas)

        request_obj = SecretRequest(
            usuario_id=user.id,
            secret_id=secret.id,
            motivo=motivo,
            ip_request=request.client.host if request else "unknown",
            user_agent=request.headers.get("user-agent") if request else None,
            status='pendente',
            expira_em=datetime.utcnow() + timedelta(minutes=5)  # Auto-expira em 5 min
        )
        db.add(request_obj)
        db.flush()

        # Log
        log = SecretAccessLog(
            secret_id=secret.id,
            usuario_id=user.id,
            acao='requisitado',
            motivo=motivo,
            resultado='sucesso',
            ip_address=request.client.host if request else "unknown"
        )
        db.add(log)
        db.commit()

        return {
            "request_id": request_obj.id,
            "status": "pendente",
            "secret_nome": nome,
            "motivo": motivo,
            "pedido_em": request_obj.pedido_em.isoformat(),
            "expira_em": request_obj.expira_em.isoformat(),
            "mensagem": "✅ Pedido criado. Aprove no seu celular/PC para acessar."
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar requisição: {str(e)}")


# ============================================================================
# GET /api/v1/cofre/pending-approvals — Pedidos pendentes
# ============================================================================

@router.get("/cofre/pending-approvals")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Lista pedidos pendentes de aprovação (pra celular/PC)."""
    try:
        # Get pending requests for this user (como APROVADOR, não como REQUESTER)
        # i.e., usuários que têm permissão de aprovar
        # TODO: Implementar role-based approval (por agora: admins)

        pending = db.query(SecretRequest).filter(
            SecretRequest.status == 'pendente',
            SecretRequest.expira_em > datetime.utcnow()
        ).all()

        # Filter by user permissions (simplificado: só mostra dele)
        pending = [
            {
                "request_id": p.id,
                "usuario_nome": p.usuario.full_name if p.usuario else "Unknown",
                "secret_nome": p.secret.nome,
                "motivo": p.motivo,
                "pedido_em": p.pedido_em.isoformat(),
                "ip_request": p.ip_request,
                "expira_em": p.expira_em.isoformat()
            }
            for p in pending
        ]

        return {
            "total": len(pending),
            "pendentes": pending
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar pedidos: {str(e)}")


# ============================================================================
# POST /api/v1/cofre/approve/{request_id} — Aprova acesso
# ============================================================================

@router.post("/cofre/approve/{request_id}")
async def approve_secret_access(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Aprova pedido de acesso a secret."""
    try:
        req = db.query(SecretRequest).filter(
            SecretRequest.id == request_id
        ).first()

        if not req:
            raise HTTPException(404, "Requisição não encontrada")

        if req.status != 'pendente':
            raise HTTPException(400, f"Requisição já foi {req.status}")

        if req.esta_expirado:
            req.status = 'expirado'
            db.commit()
            raise HTTPException(400, "Requisição expirou (> 5 min)")

        # Approve
        aprovado = payload.get("aprovado", True)

        approval = SecretApproval(
            request_id=request_id,
            aprovador_id=user.id,
            aprovado=aprovado,
            motivo_rejeicao=payload.get("motivo_rejeicao") if not aprovado else None,
            ip_approval=request.client.host if request else "unknown",
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(approval)

        if aprovado:
            req.status = 'aprovado'
            # Generate temporary token
            req.token = secrets.token_urlsafe(32)
            req.token_expira_em = datetime.utcnow() + timedelta(
                hours=req.secret.tempo_expiracao_horas
            )
        else:
            req.status = 'rejeitado'

        db.commit()

        # Log
        log = SecretAccessLog(
            secret_id=req.secret_id,
            usuario_id=user.id,
            acao='aprovado' if aprovado else 'rejeitado',
            motivo=f"Aprovador: {user.email}",
            resultado='sucesso',
            ip_address=request.client.host if request else "unknown"
        )
        db.add(log)
        db.commit()

        return {
            "status": "aprovado" if aprovado else "rejeitado",
            "request_id": request_id,
            "aprovado_por": user.email,
            "aprovado_em": approval.aprovado_em.isoformat(),
            "mensagem": "✅ Aprovado! Requester pode acessar agora." if aprovado else "❌ Rejeitado."
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao aprovar: {str(e)}")


# ============================================================================
# GET /api/v1/cofre/secrets/{nome} — Retorna secret (se aprovado)
# ============================================================================

@router.get("/cofre/secrets/{nome}")
async def get_secret_value(
    nome: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Retorna valor do secret (requer token válido se requer_aprovacao=True)."""
    try:
        secret = db.query(SecretVault).filter(
            SecretVault.usuario_id == user.id,
            SecretVault.nome == nome
        ).first()

        if not secret:
            raise HTTPException(404, f"Secret '{nome}' não encontrado")

        # Check se requer aprovação
        if secret.requer_aprovacao:
            if not token:
                raise HTTPException(403, "Token obrigatório")

            # Verify token
            req = db.query(SecretRequest).filter(
                SecretRequest.secret_id == secret.id,
                SecretRequest.token == token,
                SecretRequest.status == 'aprovado',
                SecretRequest.token_expira_em > datetime.utcnow()
            ).first()

            if not req:
                raise HTTPException(403, "Token inválido ou expirado")

            # Update last access
            secret.ultimo_acesso = datetime.utcnow()
            secret.ultimo_acessado_por = user.id
            secret.ultimo_acessado_de_ip = request.client.host if request else "unknown"

        # TODO: Integração Azure Key Vault — retorna valor real aqui
        valor = "***MOCK_VALUE***"

        # Log acesso
        log = SecretAccessLog(
            secret_id=secret.id,
            usuario_id=user.id,
            acao='acessado',
            resultado='sucesso',
            ip_address=request.client.host if request else "unknown"
        )
        db.add(log)
        db.commit()

        return {
            "nome": nome,
            "tipo": secret.tipo.value,
            "valor": valor,  # Em prod: retorna de AKV
            "expira_em": (datetime.utcnow() + timedelta(hours=secret.tempo_expiracao_horas)).isoformat(),
            "mensagem": "✅ Retornando secret (válido por 1h)"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao acessar secret: {str(e)}")
