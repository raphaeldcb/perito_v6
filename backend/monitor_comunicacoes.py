"""Monitor de comunicações judiciais por email — Microsoft Graph.

Lê emails não-lidos de uma caixa configurada, classifica como judicial ou não,
extrai dados processuais (Vara, Comarca, Número do Processo) e armazena para
acompanhamento na interface de Comunicações Judiciais.

Idempotente: utiliza external_id (internetMessageId) para evitar reprocessamento.
Separado de monitor_emails.py (que serve Intimacao) para evitar contaminação.
"""

import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ComunicacaoConfig, ComunicacaoMensagem
from app.services import graph_mail
from app.services.comunicacoes_service import ComunicacoesJudiciaisService
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)

CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def configurado() -> bool:
    """Verifica se Microsoft Graph está configurado."""
    return graph_mail.configurado()


def _texto_do_corpo(msg: dict) -> str:
    """Extrai texto limpo do corpo do email."""
    corpo = (msg.get("body") or {}).get("content", "") or msg.get("bodyPreview", "")
    # Remove tags HTML
    return re.sub(r"<[^>]+>", " ", corpo)


def processar_caixa_entrada(conta_email: str = "financeiro@ipcms.com.br", limite: int = 50) -> dict:
    """Processa emails da caixa de comunicações.

    Args:
        conta_email: Email da caixa a monitorar
        limite: Número máximo de emails a processar por execução

    Retorna:
        Dict com estatísticas: {
            "emails_processados": int,
            "emails_ignorados": int,
            "judiciais": int,
            "nao_judiciais": int,
            "erros": int
        }
    """

    if not configurado():
        logger.warning(
            "Monitor de Comunicações DESABILITADO: defina GRAPH_TENANT_ID, "
            "GRAPH_CLIENT_ID e GRAPH_CLIENT_SECRET no .env"
        )
        return {
            "emails_processados": 0,
            "emails_ignorados": 0,
            "judiciais": 0,
            "nao_judiciais": 0,
            "erros": 0,
        }

    db = SessionLocal()
    service = ComunicacoesJudiciaisService(db)
    stats = {
        "emails_processados": 0,
        "emails_ignorados": 0,
        "judiciais": 0,
        "nao_judiciais": 0,
        "erros": 0,
    }

    try:
        # Obter ou criar configuração
        config = service.obter_config(conta_email)

        # Buscar emails não-lidos
        emails = graph_mail.listar_nao_lidos(limite=limite)
        logger.info(f"📧 {len(emails)} emails não-lidos encontrados")

        for msg in emails:
            try:
                message_id = msg.get("internetMessageId") or msg["id"]

                # Verificar idempotência
                existente = db.query(ComunicacaoMensagem).filter_by(
                    external_id=message_id
                ).first()

                if existente:
                    logger.debug(f"Email {message_id} já processado, ignorando")
                    stats["emails_ignorados"] += 1
                    continue

                # Extrair campos
                assunto = msg.get("subject", "Sem assunto")
                corpo = _texto_do_corpo(msg)
                remetente = msg.get("from", {}).get("emailAddress", {})
                email_remetente = remetente.get("address", "desconhecido")
                nome_remetente = remetente.get("name", email_remetente)

                # Converter data
                data_str = msg.get("receivedDateTime", datetime.now().isoformat())
                try:
                    if data_str.endswith("Z"):
                        data_recebimento = datetime.fromisoformat(
                            data_str.replace("Z", "+00:00")
                        )
                    else:
                        data_recebimento = datetime.fromisoformat(data_str)
                except:
                    data_recebimento = datetime.now()

                # Processar mensagem
                mensagem = service.processar_mensagem(
                    external_id=message_id,
                    remetente=nome_remetente,
                    email_remetente=email_remetente,
                    assunto=assunto,
                    corpo=corpo,
                    data_recebimento=data_recebimento,
                )

                if mensagem:
                    stats["emails_processados"] += 1
                    if mensagem.eh_judicial:
                        stats["judiciais"] += 1
                    else:
                        stats["nao_judiciais"] += 1

                    # Marcar como lido (best-effort)
                    try:
                        graph_mail.marcar_lido(msg["id"])
                    except Exception as e:
                        logger.debug(f"Não foi possível marcar como lido: {e}")

            except Exception as e:
                logger.error(f"Erro processando email: {e}")
                stats["erros"] += 1
                continue

        # Registrar execução
        service.registrar_log(
            config_id=config.id,
            operacao="MONITORAMENTO",
            nivel="INFO",
            mensagem=f"Processamento concluído",
            dados=stats,
        )

        logger.info(
            f"✅ Monitoramento de Comunicações concluído: "
            f"processados={stats['emails_processados']}, "
            f"judiciais={stats['judiciais']}, "
            f"erros={stats['erros']}"
        )

        return stats

    except Exception as e:
        logger.error(f"Erro crítico no monitoramento: {e}")
        stats["erros"] += 1
        return stats

    finally:
        db.close()
