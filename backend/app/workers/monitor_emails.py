"""Monitor de emails — Microsoft Graph (caixa financeiro@ipcms.com.br).

Lê TODOS os emails não-lidos, classifica como judicial ou não, extrai dados,
salva em email_messages com análise e categorias. Idempotente: internetMessageId
vira message_id (unique). Sem credenciais Graph, declara-se desabilitado.
"""
import logging
import os
import re
from datetime import datetime

from app.models import EmailMessage
from app.services import graph_mail
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)

# CNJ formatado com separadores obrigatórios (NNNNNNN-DD.AAAA.J.TT.OOOO).
# Exigir os separadores evita casar com sequências longas de dígitos de
# códigos de barras/boletos (ex: fatura Unimed virava falsa intimação).
CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def configurado() -> bool:
    return graph_mail.configurado()


def _salvar_pdf(numero_cnj: str, nome: str, conteudo: bytes) -> str:
    base = os.path.join(settings.storage_dir, "intimacoes")
    os.makedirs(base, exist_ok=True)
    caminho = os.path.join(base, f"{numero_cnj}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{nome}")
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho


def _texto_do_corpo(msg: dict) -> str:
    corpo = (msg.get("body") or {}).get("content", "") or msg.get("bodyPreview", "")
    # remove tags HTML de forma tosca porém suficiente para regex de CNJ
    return re.sub(r"<[^>]+>", " ", corpo)


def _classificar_judicial(assunto: str, corpo: str) -> tuple[bool, float, str]:
    """Classifica se email é judicial (heurístico simples).

    Retorna: (é_judicial, confiança 0-1, motivo)
    """
    texto_lower = f"{assunto} {corpo}".lower()

    palavras_chave_judicial = [
        "intimação", "mandado", "despacho", "sentença", "apelação",
        "recurso", "processo", "tribunal", "vara", "juiz", "judicial",
        "código de processo judicial", "número do processo", "cnj"
    ]

    palavras_chave_negativas = [
        "boleto", "fatura", "cobrança", "comprovante de pagamento",
        "recebimento", "nf-e", "cupom", "nota fiscal", "nota de débito"
    ]

    # Contar palavras-chave
    score_judicial = sum(1 for p in palavras_chave_judicial if p in texto_lower)
    score_negativo = sum(1 for p in palavras_chave_negativas if p in texto_lower)

    # Heurística simples
    if score_judicial > 0 and score_negativo == 0:
        confianca = min(0.95, 0.5 + score_judicial * 0.15)
        return True, confianca, f"Detectadas {score_judicial} palavras-chave judiciais"
    elif "cnj" in texto_lower or CNJ_RE.search(texto_lower):
        return True, 0.98, "Número CNJ detectado"

    return False, 0.0, "Sem indicadores judiciais"


def processar_caixa_entrada() -> int:
    """Processa TODOS os emails não-lidos e salva em email_messages com análise."""
    if not configurado():
        logger.warning(
            "Monitor de email DESABILITADO: defina GRAPH_TENANT_ID, "
            "GRAPH_CLIENT_ID e GRAPH_CLIENT_SECRET no .env"
        )
        return 0

    processados = 0
    db = SessionLocal()
    try:
        for msg in graph_mail.listar_nao_lidos():
            internet_message_id = msg.get("internetMessageId") or msg["id"]

            # Idempotência: verificar se já foi processado
            ja_existe = (
                db.query(EmailMessage)
                .filter(EmailMessage.internet_message_id == internet_message_id)
                .first()
            )
            if ja_existe:
                logger.debug(f"Email {internet_message_id[:20]}... já processado")
                graph_mail.marcar_lido(msg["id"])
                continue

            # Extrair remetente (melhorado)
            from_data = msg.get("from", {})
            from_obj = from_data.get("emailAddress", {}) if isinstance(from_data, dict) else {}
            from_addr = from_obj.get("address", "").strip() if from_obj else ""
            from_name = from_obj.get("name", "").strip() if from_obj else ""

            # Debug log
            if not from_addr:
                logger.warning(f"⚠️ from_address vazio para email {msg.get('id', 'unknown')[:20]}. from_data={from_data}")

            # Fallback: se não tiver endereço, tenta usar name; se nada, marca como desconhecido
            if not from_addr and not from_name:
                from_addr = "Remetente Desconhecido"
            elif not from_addr and from_name:
                from_addr = from_name

            to_addresses = ",".join([
                addr.get("emailAddress", {}).get("address", "")
                for addr in msg.get("toRecipients", [])
            ]) or ""
            cc_addresses = ",".join([
                addr.get("emailAddress", {}).get("address", "")
                for addr in msg.get("ccRecipients", [])
            ]) or ""

            assunto = msg.get("subject") or ""
            corpo_texto = _texto_do_corpo(msg)
            corpo_html = msg.get("body", {}).get("content", "") or ""
            received_dt = msg.get("receivedDateTime") or datetime.utcnow().isoformat()

            # Classificar como judicial
            is_judicial, confianca, motivo = _classificar_judicial(assunto, corpo_texto)

            # Extrair CNJ se houver
            numero_cnj = None
            match = CNJ_RE.search(f"{assunto}\n{corpo_texto}")
            if match:
                numero_cnj = match.group(0)

            # Processar anexos com info visual
            has_attachments = msg.get("hasAttachments", False)
            attachments_data = None
            if has_attachments:
                try:
                    anexos = []
                    for nome, conteudo in graph_mail.baixar_anexos_pdf(msg["id"]):
                        tamanho_kb = round(len(conteudo) / 1024, 2)
                        anexos.append({"nome": nome, "tamanho_kb": tamanho_kb})
                    if anexos:
                        count = len(anexos)
                        nomes = ", ".join([f"{a['nome']} ({a['tamanho_kb']} KB)" for a in anexos])
                        attachments_data = f"📎 {count} {'arquivo' if count == 1 else 'arquivos'}: {nomes}"
                except Exception as e:
                    logger.warning(f"Falha ao processar anexos: {e}")
                    # Mesmo com falha, marca que tem anexos
                    attachments_data = "📎 Anexos presentes (detalhes indisponíveis)"

            # Salvar em email_messages
            email_record = EmailMessage(
                message_id=msg["id"],
                internet_message_id=internet_message_id,
                conversation_id=msg.get("conversationId") or "",
                from_address=from_addr,
                from_name=from_name,
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                subject=assunto[:500],
                body_text=corpo_texto[:50000],
                body_html=corpo_html[:50000],
                received_datetime=received_dt,
                is_judicial=is_judicial,
                judicial_confidence=confianca,
                judicial_reason=motivo,
                numero_processo=numero_cnj,
                status="novo",
                has_attachments=has_attachments,
                attachments_data=attachments_data,
                analyzed_at=datetime.utcnow(),
                categories="ANALISADO PELO PERITO V6",
            )
            db.add(email_record)
            db.commit()

            # Marcar como lido e aplicar categoria no Outlook
            try:
                graph_mail.marcar_lido(msg["id"])
                graph_mail.adicionar_categoria(msg["id"], "ANALISADO PELO PERITO V6")
            except Exception as e:
                logger.warning(f"Falha ao marcar categoria no Outlook: {e}")

            processados += 1
            logger.info(f"✅ Email analisado: {from_addr} — '{assunto[:60]}' — judicial={is_judicial}")

    except Exception as e:
        logger.error(f"Erro ao processar caixa de entrada: {e}", exc_info=True)
    finally:
        db.close()

    return processados
