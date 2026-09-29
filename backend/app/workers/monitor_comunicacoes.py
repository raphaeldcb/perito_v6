"""Monitor de comunicações judiciais por email — Microsoft Graph."""

import json
import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import EmailMessage, EmailConfig
from app.services import graph_mail
from app.services.comunicacoes_service import ComunicacoesService
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)

CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def configurado() -> bool:
    """Verifica se Microsoft Graph está configurado."""
    return graph_mail.configurado()


def _texto_do_corpo(msg: dict) -> str:
    """Extrai texto limpo do corpo do email."""
    corpo = (msg.get("body") or {}).get("content", "") or msg.get("bodyPreview", "")
    return re.sub(r"<[^>]+>", " ", corpo)


def processar_caixa_entrada(conta_email: str = "financeiro@ipcms.com.br", limite: int = 50) -> dict:
    """Processa emails da caixa de comunicações."""

    if not configurado():
        logger.warning("Monitor de Comunicações DESABILITADO: configure Graph API no .env")
        return {"processados": 0, "ignorados": 0, "judiciais": 0, "erros": 0}

    db = SessionLocal()
    service = ComunicacoesService(db)
    stats = {"processados": 0, "ignorados": 0, "judiciais": 0, "erros": 0}

    try:
        emails = graph_mail.listar_nao_lidos(limite=limite)
        logger.info(f"📧 {len(emails)} emails não-lidos")

        for msg in emails:
            try:
                message_id = msg.get("internetMessageId") or msg["id"]
                existente = db.query(EmailMessage).filter_by(internet_message_id=message_id).first()
                if existente:
                    stats["ignorados"] += 1
                    continue

                assunto = msg.get("subject", "Sem assunto")
                corpo = _texto_do_corpo(msg)
                remetente = msg.get("from", {}).get("emailAddress", {})
                email_remetente = remetente.get("address", "desconhecido")
                nome_remetente = remetente.get("name", email_remetente)

                data_str = msg.get("receivedDateTime", datetime.now().isoformat())
                try:
                    if data_str.endswith("Z"):
                        data_recebimento = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                    else:
                        data_recebimento = datetime.fromisoformat(data_str)
                except:
                    data_recebimento = datetime.now()

                email_msg = EmailMessage(
                    message_id=msg["id"],
                    internet_message_id=message_id,
                    from_address=email_remetente,
                    from_name=nome_remetente,
                    to_addresses=json.dumps([e.get("emailAddress", {}).get("address") for e in msg.get("toRecipients", [])]),
                    subject=assunto,
                    body_text=corpo,
                    body_html=msg.get("body", {}).get("content", ""),
                    received_datetime=data_recebimento,
                    is_judicial=False,
                )

                if re.search(r"intimação|judicial|processo|vara|comarca", assunto.lower()):
                    email_msg.is_judicial = True
                    stats["judiciais"] += 1
                    match = CNJ_RE.search(assunto + " " + corpo)
                    if match:
                        email_msg.numero_processo = match.group()

                db.add(email_msg)
                db.commit()
                stats["processados"] += 1

                try:
                    graph_mail.marcar_lido(msg["id"])
                except:
                    pass

            except Exception as e:
                logger.error(f"Erro: {e}")
                stats["erros"] += 1
                db.rollback()

        logger.info(f"✅ Monitoramento: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        stats["erros"] += 1
        return stats

    finally:
        db.close()
