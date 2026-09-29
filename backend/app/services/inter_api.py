"""Integração com Banco Inter — OAuth2 + API calls + Reconciliação.

Phase 1: Saldo, Extrato, Webhook → Auto-reconciliar com lançamento_bancario
"""
import os
import hmac
import hashlib
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# URLs da Inter API
INTER_API_URL = "https://api.bancointer.com.br/v2"
INTER_OAUTH_URL = "https://oauth.bancointer.com.br/oauth/authorize"
INTER_TOKEN_URL = "https://oauth.bancointer.com.br/oauth/token"

# Sandbox
INTER_API_SANDBOX = "https://api-sandbox.bancointer.com.br/v2"
INTER_TOKEN_SANDBOX = "https://oauth-sandbox.bancointer.com.br/oauth/token"

# Config
INTER_CLIENT_ID = os.getenv("INTER_CLIENT_ID", "")
INTER_CLIENT_SECRET = os.getenv("INTER_CLIENT_SECRET", "")
INTER_CERT_PATH = os.getenv("INTER_CERT_PATH", "")
INTER_KEY_PATH = os.getenv("INTER_KEY_PATH", "")
INTER_AMBIENTE = os.getenv("INTER_AMBIENTE", "sandbox")


def _api_url():
    return INTER_API_SANDBOX if INTER_AMBIENTE == "sandbox" else INTER_API_URL


def _token_url():
    return INTER_TOKEN_SANDBOX if INTER_AMBIENTE == "sandbox" else INTER_TOKEN_URL


async def obter_token(refresh_token: Optional[str] = None) -> dict:
    """OAuth2: obter access_token (client credentials ou refresh)."""
    async with httpx.AsyncClient(verify=False) as client:
        if refresh_token:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": INTER_CLIENT_ID,
                "client_secret": INTER_CLIENT_SECRET,
            }
        else:
            data = {
                "grant_type": "client_credentials",
                "client_id": INTER_CLIENT_ID,
                "client_secret": INTER_CLIENT_SECRET,
                "scope": "consulta_saldo extrato_bancario pix webhook",
            }

        try:
            resp = await client.post(_token_url(), data=data)
            resp.raise_for_status()
            token_data = resp.json()
            if "expires_in" in token_data:
                token_data["expires_at"] = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            return {"ok": True, "data": token_data}
        except Exception as e:
            logger.error(f"Inter OAuth: {str(e)}")
            return {"ok": False, "erro": str(e)}


async def consultar_saldo(access_token: str) -> dict:
    """GET /saldo — Saldo atual da conta."""
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        try:
            resp = await client.get(
                f"{_api_url()}/saldo",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            )
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except Exception as e:
            logger.error(f"Inter saldo: {str(e)}")
            return {"ok": False, "erro": str(e)}


async def consultar_extrato(
    access_token: str,
    data_inicio: str,
    data_fim: str,
    limite: int = 100
) -> dict:
    """GET /extrato — Movimentações entre datas (até 90 dias).

    Response: {dadosExtrato: {movimentacoes: [...]}}
    """
    async with httpx.AsyncClient(verify=False, timeout=15) as client:
        try:
            resp = await client.get(
                f"{_api_url()}/extrato",
                params={"dataInicio": data_inicio, "dataFim": data_fim, "limite": limite},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except Exception as e:
            logger.error(f"Inter extrato: {str(e)}")
            return {"ok": False, "erro": str(e)}


def validar_webhook_assinatura(payload: bytes, assinatura: str, webhook_secret: str) -> bool:
    """HMAC-SHA256: valida assinatura do webhook.

    Inter envia: X-Signature: base64(HMAC-SHA256(payload, secret))
    """
    esperado = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).digest()

    import base64
    try:
        recebido = base64.b64decode(assinatura)
        return hmac.compare_digest(esperado, recebido)
    except Exception as e:
        logger.error(f"Webhook signature validation failed: {e}")
        return False


def processar_webhook_pix_recebido(payload_json: dict, conta_id: int) -> dict:
    """Processa webhook 'pixRecebido' — cria InterTransaction + reconcilia com lançamento_bancario.

    Payload: {pix: {id, valor, horario, pagador: {chave, nome}, infoPagador: "..."}}
    """
    try:
        pix_info = payload_json.get("pix", {})

        return {
            "ok": True,
            "inter_id": pix_info.get("id"),
            "valor": float(pix_info.get("valor", 0)),
            "data": pix_info.get("horario"),
            "descricao": f"Pix recebido de {pix_info.get('pagador', {}).get('nome', '?')}",
            "tipo": "credito",
            "status": "confirmado",
        }
    except Exception as e:
        logger.error(f"Webhook PIX parse error: {e}")
        return {"ok": False, "erro": str(e)}
