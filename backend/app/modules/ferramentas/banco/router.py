"""Banco Module — Banking integrations (Inter, TJMS).

Consolidates:
- v6/backend/app/routes/inter_banco.py (OAuth, saldo, extrato, boletos, webhooks)
- v6/backend/app/routes/inter_api.py (PIX transfers, balance, transaction webhooks)
- v6/backend/app/routes/tjms.py (TJMS document download)
"""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.middleware import get_current_user, exigir_admin
from app.models import User, Job
from app.models.inter import InterAccount, InterTransaction, InterWebhook, InterBoleto
from app.models.inter_transacao import InterTransacao, StatusTransacao, TipoOperacao
from app.services import get_db
from app.services.inter_api import (
    obter_token, consultar_saldo, consultar_extrato, validar_webhook_assinatura,
    processar_webhook_pix_recebido
)
from app.services.inter_reconciliation import sincronizar_extrato_completo, reconciliar_transacao_inter
from app.services.inter_api_client import InterAPIClient
from app.services.tjms_downloader import download_autos_tjms
from app.decorators.require_feature import require_feature_flag

from .schemas import (
    InterConnectRequest,
    ExtratoBuscaRequest,
    BoletoEmitirRequest,
    PixTransferRequest,
    WebhookPagamentoConfirmado,
    DownloadRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/banco", tags=["banco"])


# ============================================================================
# INTER OAUTH & ACCOUNT MANAGEMENT
# ============================================================================

@router.post("/inter/connect")
async def conectar_inter(
    payload: InterConnectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Conecta conta do Inter (OAuth callback).

    Bruno autentica no Inter, volta com código.
    Sistema troca código por access_token.
    """
    token_resp = await obter_token()  # client_credentials flow
    if not token_resp["ok"]:
        raise HTTPException(status_code=400, detail=f"Erro OAuth: {token_resp['erro']}")

    token_data = token_resp["data"]

    # Criar ou atualizar InterAccount
    conta = db.query(InterAccount).filter(
        InterAccount.usuario_id == user.id
    ).first()

    if not conta:
        conta = InterAccount(usuario_id=user.id)

    conta.access_token = token_data["access_token"]
    conta.refresh_token = token_data.get("refresh_token")
    conta.token_expira_em = token_data.get("expires_at")
    conta.scope = token_data.get("scope")

    db.add(conta)
    db.commit()
    db.refresh(conta)

    return {
        "ok": True,
        "mensagem": "Conta Inter conectada com sucesso",
        "conta_id": conta.id,
    }


# ============================================================================
# INTER SALDO & EXTRATO
# ============================================================================

@router.get("/inter/saldo")
async def consultar_saldo_inter(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Consulta saldo atual — atualiza cache no Perito."""
    conta = db.query(InterAccount).filter(
        InterAccount.usuario_id == user.id
    ).first()

    if not conta or not conta.access_token:
        raise HTTPException(status_code=404, detail="Conta Inter não conectada")

    # Refresh token se expirado
    if conta.token_expira_em and datetime.utcnow() > conta.token_expira_em:
        token_resp = await obter_token(conta.refresh_token)
        if not token_resp["ok"]:
            raise HTTPException(status_code=400, detail="Token refresh falhou")
        token_data = token_resp["data"]
        conta.access_token = token_data["access_token"]
        conta.token_expira_em = token_data.get("expires_at")
        db.commit()

    saldo_resp = await consultar_saldo(conta.access_token)
    if not saldo_resp["ok"]:
        raise HTTPException(status_code=400, detail=saldo_resp["erro"])

    # Cache
    saldo_dados = saldo_resp["data"].get("saldo", {})
    conta.saldo = saldo_dados.get("saldoDisponivel", 0)
    db.commit()

    return saldo_resp["data"]


@router.post("/inter/extrato")
async def consultar_extrato_inter(
    payload: ExtratoBuscaRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Consulta extrato + AUTO-RECONCILIA com lançamento_bancario."""
    conta = db.query(InterAccount).filter(
        InterAccount.usuario_id == user.id
    ).first()

    if not conta or not conta.access_token:
        raise HTTPException(status_code=404, detail="Conta Inter não conectada")

    extrato_resp = await consultar_extrato(
        conta.access_token,
        payload.data_inicio,
        payload.data_fim
    )

    if not extrato_resp["ok"]:
        raise HTTPException(status_code=400, detail=extrato_resp["erro"])

    # Sincronizar + reconciliar
    resultado = sincronizar_extrato_completo(
        db,
        conta.id,
        extrato_resp["data"]
    )

    return {
        "ok": True,
        "reconciliacao": resultado,
        "conta_id": conta.id,
    }


# ============================================================================
# INTER BOLETOS & COBRANÇAS
# ============================================================================

@router.post("/inter/boleto/emitir")
async def emitir_boleto_inter(
    payload: BoletoEmitirRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Emite boleto no Inter.

    ⚠️ NOTE: emitir_boleto() function not defined in services. Incomplete feature.
    """
    conta = db.query(InterAccount).filter(
        InterAccount.usuario_id == user.id
    ).first()

    if not conta or not conta.access_token:
        raise HTTPException(status_code=404, detail="Conta Inter não conectada")

    # TODO: Implement emitir_boleto service call
    raise HTTPException(status_code=501, detail="Recurso não implementado")


# ============================================================================
# INTER WEBHOOKS (Account notifications)
# ============================================================================

@router.post("/inter/webhook")
async def receber_webhook_inter(
    request: Request,
    db: Session = Depends(get_db),
):
    """Webhook: Inter notifica eventos → Auto-reconciliação.

    Tipos suportados:
    - pixRecebido: Crédito Pix → reconciliar com lançamento_bancario
    - cobrancaPaga: Cobrança paga → marcar como paga
    - bolotoPago: Boleto pago → marcar como pago
    """
    body = await request.body()
    assinatura = request.headers.get("X-Signature", "")

    # Encontrar conta por webhook_secret (match exato)
    conta = db.query(InterAccount).filter(
        InterAccount.webhook_ativo == True,
        InterAccount.webhook_secret != None
    ).first()

    if not conta:
        return {"ok": False, "erro": "Conta não configurada", "status": 404}

    # Validar assinatura
    valido = validar_webhook_assinatura(body, assinatura, conta.webhook_secret or "")
    if not valido:
        return {"ok": False, "erro": "Assinatura inválida", "status": 401}

    payload = json.loads(body)
    tipo_evento = payload.get("tipo", "desconhecido")

    # Registrar webhook
    wh = InterWebhook(
        conta_id=conta.id,
        tipo_evento=tipo_evento,
        payload=payload,
        assinatura=assinatura,
        validado=True,
    )
    db.add(wh)
    db.flush()

    # Processar conforme tipo
    if tipo_evento == "pixRecebido":
        pix_resultado = processar_webhook_pix_recebido(payload, conta.id)
        if pix_resultado["ok"]:
            # Reconciliar direto
            reconciliar_resultado = reconciliar_transacao_inter(
                db,
                pix_resultado["inter_id"],
                pix_resultado["valor"],
                pix_resultado["data"],
                pix_resultado["descricao"],
                pix_resultado["tipo"],
                conta.id
            )
            wh.processado = reconciliar_resultado["ok"]
            if reconciliar_resultado.get("matched"):
                wh.payload["reconciliacao"] = {"matched": True, "lancamento_id": reconciliar_resultado.get("lancamento_id")}

    db.commit()

    return {
        "ok": True,
        "webhook_id": wh.id,
        "tipo": tipo_evento,
        "processado": wh.processado,
    }


# ============================================================================
# PIX TRANSFERS (InterTransacao flow)
# ============================================================================

@router.post("/pix/transfer")
async def pix_transfer(
    request: PixTransferRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Executa transferência PIX via Banco Inter.

    Cria registro InterTransacao e dispara chamada para API.
    Retorna transaction_id para rastreamento.
    """
    try:
        # Validar usuário tem permissão (admin ou próprio coletador)
        if user.role.name != "admin":
            raise HTTPException(
                status_code=403,
                detail="Apenas admin pode executar transferências"
            )

        # Usar cliente singleton para reutilizar token
        inter_client = InterAPIClient.get_instance()

        # ID único para idempotência (mesmo se requisição falha e retry)
        id_unico = str(uuid.uuid4())

        # Criar registro de transação (antes de chamar API)
        transacao = InterTransacao(
            id_unico=id_unico,
            tipo_operacao=TipoOperacao.PIX,
            descricao=request.descricao,
            valor_centavos=request.valor_centavos,
            valor_real=request.valor_centavos / 100,
            chave_destino=request.chave_destino,
            status=StatusTransacao.PENDENTE,
            iniciado_por_user_id=user.id,
            coletador_id=request.coletador_id,
            process_id=request.processo_id,
            tentativas=1,
        )
        db.add(transacao)
        db.flush()

        logger.info(
            f"Iniciando PIX transfer: {id_unico} "
            f"→ {request.chave_destino} "
            f"R$ {transacao.valor_real:.2f}"
        )

        # Chamar API Banco Inter
        response = inter_client.pix_transfer(
            chave_destino=request.chave_destino,
            valor=request.valor_centavos,
            descricao=request.descricao,
            id_unico=id_unico
        )

        # Atualizar registro com resposta
        transacao.transaction_id = response.get("transaction_id")
        transacao.status = StatusTransacao.PROCESSANDO
        transacao.resposta_banco = str(response)

        db.commit()
        db.refresh(transacao)

        logger.info(f"PIX transfer aprovado: {transacao.transaction_id}")

        return {
            "status": "sucesso",
            "transacao_id": transacao.id,
            "transaction_id": transacao.transaction_id,
            "valor": transacao.valor_real,
            "chave": request.chave_destino,
            "status_banco": transacao.status
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Erro em PIX transfer: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar transferência: {str(e)[:100]}"
        )


@router.get("/balance")
async def get_balance(
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Consulta saldo da conta no Banco Inter."""
    try:
        inter_client = InterAPIClient.get_instance()
        balance_data = inter_client.get_balance()

        return {
            "status": "sucesso",
            "saldo": balance_data.get("saldo"),
            "disponivel": balance_data.get("disponivel"),
            "bloqueado": balance_data.get("bloqueado"),
            "data_consulta": balance_data.get("data")
        }

    except Exception as e:
        logger.error(f"Erro ao consultar saldo: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao consultar saldo")


@router.post("/webhook/pagamento-confirmado")
async def webhook_pagamento_confirmado(
    payload: WebhookPagamentoConfirmado,
    db: Session = Depends(get_db),
):
    """
    Webhook do Banco Inter — notifica quando pagamento foi confirmado.

    Segurança:
    - Validar assinatura do webhook (HMAC-SHA256)
    - Validar IP origem (allowlist do Banco Inter)
    - Idempotência: não processar 2x mesmo webhook
    """
    try:
        # TODO: Validar assinatura do webhook (HMAC)
        # TODO: Validar IP origem

        logger.info(f"Webhook recebido: transaction_id={payload.transaction_id} status={payload.status}")

        # Procurar transação no BD
        transacao = db.query(InterTransacao).filter(
            InterTransacao.transaction_id == payload.transaction_id
        ).first()

        if not transacao:
            logger.warning(f"Transação não encontrada: {payload.transaction_id}")
            return {"status": "ignorado", "motivo": "transacao_nao_encontrada"}

        # Atualizar status
        if payload.status == "APPROVED":
            transacao.status = StatusTransacao.APROVADO
            logger.info(f"Transação aprovada: {transacao.id}")
        else:
            transacao.status = StatusTransacao.FALHOU
            transacao.status_detalhe = payload.motivo_rejeicao or "Rejeitado pelo banco"
            logger.warning(f"Transação rejeitada: {transacao.id} — {payload.motivo_rejeicao}")

        transacao.confirmado_em = payload.data_confirmacao

        db.commit()

        return {
            "status": "processado",
            "transacao_id": transacao.id,
            "novo_status": transacao.status
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao processar webhook: {str(e)}", exc_info=True)
        return {"status": "erro", "motivo": str(e)[:100]}


@router.get("/transacoes")
async def listar_transacoes(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Lista todas as transações (admin only)."""
    query = db.query(InterTransacao)

    if status:
        query = query.filter(InterTransacao.status == status)

    total = query.count()
    transacoes = query.order_by(
        InterTransacao.criado_em.desc()
    ).offset(skip).limit(limit).all()

    return {
        "total": total,
        "itens": [
            {
                "id": t.id,
                "id_unico": t.id_unico,
                "tipo": t.tipo_operacao,
                "valor": t.valor_real,
                "status": t.status,
                "chave": t.chave_destino,
                "criado_em": t.criado_em.isoformat() if t.criado_em else None,
                "confirmado_em": t.confirmado_em.isoformat() if t.confirmado_em else None,
            }
            for t in transacoes
        ]
    }


# ============================================================================
# TJMS DOCUMENT DOWNLOAD
# ============================================================================

@router.post("/tjms/download-autos")
async def download_autos(
    req: DownloadRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download de autos TJMS: login → consulta → PDF"""

    cpf = os.environ.get("CPF_ESAJ", "")
    senha = os.environ.get("SENHA_ESAJ", "")

    if not cpf or not senha:
        raise HTTPException(status_code=400, detail="CPF_ESAJ ou SENHA_ESAJ não configurados")

    try:
        # Download síncro (roda em background idealmente)
        resultado = download_autos_tjms(cpf, senha, req.cnj)

        if resultado:
            return {
                "status": "sucesso",
                "cnj": req.cnj,
                "arquivo": str(resultado),
                "tamanho_kb": resultado.stat().st_size / 1024,
            }
        else:
            return {
                "status": "erro",
                "cnj": req.cnj,
                "mensagem": "Falha ao baixar autos (verifique logs)",
            }

    except Exception as e:
        return {
            "status": "erro",
            "cnj": req.cnj,
            "erro": str(e),
        }
