import logging
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import Delegacao, User
from app.services.graph_mail import enviar_email

logger = logging.getLogger(__name__)


def enviar_email_delegacao(db: Session, delegacao: Delegacao) -> bool:
    """Envia email ao prestador notificando da delegação."""
    try:
        prestador = db.query(User).filter(User.id == delegacao.prestador_id).first()
        if not prestador:
            logger.error(f"Prestador {delegacao.prestador_id} não encontrado")
            return False

        assunto = f"Delegação: {delegacao.tipo} — R$ {delegacao.valor}"
        corpo = f"""
Você foi delegado para:
{delegacao.tipo}

Valor: R$ {delegacao.valor}
Prazo: {delegacao.prazo_dias} dias
Descrição: {delegacao.descricao or "Sem descrição"}

Acesse o sistema para aceitar ou recusar.
        """.strip()

        enviar_email(
            destinatario=prestador.email,
            assunto=assunto,
            corpo=corpo
        )
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar email de delegação {delegacao.id}: {e}")
        return False


def enviar_email_resposta_delegacao(
    db: Session,
    delegacao: Delegacao,
    aceito: bool,
    motivo: str | None = None
) -> bool:
    """Envia email ao analista com resposta sobre delegação."""
    try:
        analista = db.query(User).filter(User.id == delegacao.analista_id).first()
        if not analista:
            logger.error(f"Analista {delegacao.analista_id} não encontrado")
            return False

        if aceito:
            assunto = f"Delegação ACEITA: {delegacao.tipo}"
            corpo = f"Sua delegação foi ACEITA pelo prestador."
        else:
            assunto = f"Delegação RECUSADA: {delegacao.tipo}"
            corpo = f"""
Sua delegação foi RECUSADA.

Motivo: {motivo or "Não informado"}
            """.strip()

        enviar_email(
            destinatario=analista.email,
            assunto=assunto,
            corpo=corpo
        )
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar resposta delegação {delegacao.id}: {e}")
        return False
