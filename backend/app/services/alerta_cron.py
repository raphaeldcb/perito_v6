import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoAlerta
from app.services.graph_mail import enviar_email

logger = logging.getLogger(__name__)


def calcular_status_alerta(dias_para_vencer: int, tipo: str) -> str:
    """Calcula status de cor baseado em dias para vencer."""
    if tipo == "LAUDO":
        if dias_para_vencer > 7:
            return "VERDE"
        elif 1 <= dias_para_vencer <= 7:
            return "AMARELO"
        else:
            return "VERMELHO"
    elif tipo == "OFICIO":
        if dias_para_vencer > 2:
            return "VERDE"
        elif 1 <= dias_para_vencer <= 2:
            return "AMARELO"
        else:
            return "VERMELHO"
    return "VERMELHO"


def gerar_mensagem_alerta(tipo: str, dias: int, processo_id: int) -> str:
    """Gera mensagem humanizada do alerta."""
    if dias <= 0:
        return f"{tipo} vencido para processo {processo_id}"
    return f"{tipo} vence em {dias} dia(s) para processo {processo_id}"


def verificar_e_atualizar_alertas(db: Session) -> dict:
    """Verifica prazos e cria/atualiza alertas."""
    agora = datetime.utcnow()
    laudos = db.query(Laudo).filter(Laudo.ativo == True).all()

    alertas_criados = 0
    alertas_atualizados = 0
    emails_enviados = 0

    for laudo in laudos:
        # LAUDO: prazo 7 dias (exemplo)
        prazo_laudo = laudo.data_emissao + timedelta(days=7)
        dias_laudo = (prazo_laudo - agora).days

        # Verifica alerta LAUDO
        alerta_laudo = db.query(LaudoAlerta).filter(
            LaudoAlerta.laudo_id == laudo.id,
            LaudoAlerta.tipo == "LAUDO"
        ).first()

        status_laudo = calcular_status_alerta(dias_laudo, "LAUDO")
        msg_laudo = gerar_mensagem_alerta("Laudo", dias_laudo, laudo.processo_id)

        if alerta_laudo:
            alerta_laudo.status = status_laudo
            alerta_laudo.dias_para_vencer = dias_laudo
            alerta_laudo.mensagem = msg_laudo
            alertas_atualizados += 1
        else:
            alerta_laudo = LaudoAlerta(
                laudo_id=laudo.id,
                tipo="LAUDO",
                status=status_laudo,
                dias_para_vencer=dias_laudo,
                data_vencimento=prazo_laudo,
                mensagem=msg_laudo
            )
            db.add(alerta_laudo)
            alertas_criados += 1

        # Enviar email D-7 para LAUDO
        if dias_laudo == 7 and not alerta_laudo.email_enviado:
            try:
                perito_email = laudo.perito.email if laudo.perito else "admin@ipcms.com.br"
                enviar_email(
                    destinatario=perito_email,
                    assunto=f"Alerta: Laudo vence em 7 dias - Processo {laudo.processo_id}",
                    corpo=f"Seu laudo para o processo {laudo.processo_id} vence em 7 dias. Status: {msg_laudo}"
                )
                alerta_laudo.email_enviado = datetime.utcnow()
                emails_enviados += 1
            except Exception as e:
                logger.error(f"Falha ao enviar email de alerta laudo {laudo.id}: {e}")

    db.commit()

    return {
        "alertas_criados": alertas_criados,
        "alertas_atualizados": alertas_atualizados,
        "emails_enviados": emails_enviados
    }
