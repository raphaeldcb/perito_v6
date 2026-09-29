"""Cliente Microsoft Graph para a caixa de intimações (OAuth client credentials).

Permissões de aplicativo já concedidas no Azure: Mail.Read + Mail.Send.
Env: GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_MAILBOX.
"""
import base64
import logging
import os
import time

import requests

from app.utils import retry, get_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)

TENANT_ID = os.environ.get("GRAPH_TENANT_ID", "")
CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GRAPH_CLIENT_SECRET", "")
MAILBOX = os.environ.get("GRAPH_MAILBOX", "ipcms@ipcms.com.br")

GRAPH = "https://graph.microsoft.com/v1.0"

_token_cache = {"token": None, "expira": 0}


def configurado() -> bool:
    return bool(TENANT_ID and CLIENT_ID and CLIENT_SECRET and MAILBOX)


def _token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expira"] - 60:
        return _token_cache["token"]

    resp = requests.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    corpo = resp.json()
    if "access_token" not in corpo:
        raise RuntimeError(f"Falha no token Graph: {corpo.get('error_description', corpo)[:300]}")
    _token_cache["token"] = corpo["access_token"]
    _token_cache["expira"] = time.time() + int(corpo.get("expires_in", 3600))
    return _token_cache["token"]


def _get(path: str, params: dict = None) -> dict:
    resp = requests.get(
        f"{GRAPH}{path}",
        headers={"Authorization": f"Bearer {_token()}"},
        params=params or {},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def listar_nao_lidos(limite: int = 50) -> list[dict]:
    corpo = _get(
        f"/users/{MAILBOX}/mailFolders/inbox/messages",
        {
            "$filter": "isRead eq false",
            "$top": limite,
            "$select": "id,internetMessageId,subject,bodyPreview,body,hasAttachments,receivedDateTime,from,toRecipients,ccRecipients",
            "$orderby": "receivedDateTime desc",
        },
    )
    return corpo.get("value", [])


def baixar_anexos_pdf(message_id: str) -> list[tuple[str, bytes]]:
    corpo = _get(f"/users/{MAILBOX}/messages/{message_id}/attachments")
    pdfs = []
    for anexo in corpo.get("value", []):
        nome = anexo.get("name", "")
        if nome.lower().endswith(".pdf") and anexo.get("contentBytes"):
            pdfs.append((nome, base64.b64decode(anexo["contentBytes"])))
    return pdfs


def marcar_lido(message_id: str) -> None:
    """Best-effort: exige Mail.ReadWrite (o app tem só Mail.Read). Sem essa
    permissão o email fica não-lido, mas a deduplicação por external_id já
    impede reprocessamento — não é erro fatal."""
    try:
        requests.patch(
            f"{GRAPH}/users/{MAILBOX}/messages/{message_id}",
            headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
            json={"isRead": True},
            timeout=30,
        ).raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            logger.debug("Sem permissão Mail.ReadWrite para marcar lido (opcional)")
        else:
            logger.warning(f"Falha ao marcar email como lido: {e}")


def buscar_codigo_2fa(desde_iso: str = None, caixa: str = None) -> str | None:
    """Procura o código de validação do e-SAJ (6 dígitos) na caixa.

    Só considera o email de validação (remetente saj-envio@tjms + assunto
    'Validação de identificação'), para nunca confundir com o número de um
    processo. Filtra por data para não pegar código expirado.
    """
    import re

    mailbox = caixa or MAILBOX
    params = {
        "$top": 15,
        "$select": "subject,bodyPreview,body,from,receivedDateTime",
        "$orderby": "receivedDateTime desc",
    }
    if desde_iso:
        params["$filter"] = f"receivedDateTime ge {desde_iso}"

    corpo = _get(f"/users/{mailbox}/mailFolders/inbox/messages", params)
    for msg in corpo.get("value", []):
        remetente = ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
        assunto = (msg.get("subject") or "").lower()
        eh_validacao = "saj-envio" in remetente or "validação de identificação" in assunto or "validacao de identificacao" in assunto
        if not eh_validacao:
            continue
        texto = f"{msg.get('subject', '')} {msg.get('bodyPreview', '')} {(msg.get('body') or {}).get('content', '')}"
        m = re.search(r"(?<!\d)(\d{6})(?!\d)", re.sub(r"<[^>]+>", " ", texto))
        if m:
            return m.group(1)
    return None


def listar_autos_desde(data_iso: str = "2026-01-01T00:00:00Z") -> list[dict]:
    """Lista todos os emails com PDFs anexados desde uma data.

    Retorna lista com: email_id, data_recebimento, remetente, assunto, lista de PDFs.
    """
    corpo = _get(
        f"/users/{MAILBOX}/mailFolders/inbox/messages",
        {
            "$filter": f"receivedDateTime ge {data_iso} and hasAttachments eq true",
            "$top": 200,
            "$select": "id,subject,from,receivedDateTime,hasAttachments",
            "$orderby": "receivedDateTime desc",
        },
    )

    resultado = []
    for msg in corpo.get("value", []):
        msg_id = msg.get("id")
        anexos = baixar_anexos_pdf(msg_id)
        if anexos:
            remetente = ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "")
            resultado.append({
                "id": msg_id,
                "data": msg.get("receivedDateTime", ""),
                "de": remetente,
                "assunto": msg.get("subject", ""),
                "pdfs": [nome for nome, _ in anexos],
                "qtd_pdfs": len(anexos),
            })
    return resultado


def enviar_email(para: str, assunto: str, corpo_html: str) -> None:
    requests.post(
        f"{GRAPH}/users/{MAILBOX}/sendMail",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={
            "message": {
                "subject": assunto,
                "body": {"contentType": "HTML", "content": corpo_html},
                "toRecipients": [{"emailAddress": {"address": para}}],
            },
            "saveToSentItems": True,
        },
        timeout=30,
    ).raise_for_status()
    logger.info(f"📤 Email enviado para {para}: {assunto!r}")


def adicionar_categoria(message_id: str, categoria: str) -> dict | None:
    """Sinaliza email com categoria no Outlook.

    Adiciona categoria (marcador visual) ao email. A categoria é automaticamente
    criada no Outlook quando adicionada ao primeiro email.

    Categorias aparecem como tags sinaluzadas visualmente nos emails.

    Retorna: dict com resposta da API ou None se falha.
    """
    try:
        # Adiciona a categoria ao email
        # Outlook cria a categoria automaticamente na primeira vez
        resp = requests.patch(
            f"{GRAPH}/users/{MAILBOX}/messages/{message_id}",
            headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
            json={"categories": [categoria]},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info(f"✅ Email {message_id} sinalizado com categoria '{categoria}' no Outlook")
        return resp.json() if resp.text else {"status": "success", "categoria": categoria}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            logger.warning(f"Sem permissão Mail.ReadWrite — categoria não adicionada ao Outlook")
            logger.warning(f"Detalhes da resposta: {e.response.text[:200]}")
            return None
        else:
            logger.warning(f"Falha ao adicionar categoria (HTTP {e.response.status_code if e.response else 'desconhecido'}): {e}")
            if e.response is not None:
                logger.warning(f"Response body: {e.response.text[:300]}")
            return None
    except Exception as e:
        logger.error(f"Erro ao adicionar categoria: {e}")
        return None
