import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User
from app.services.graph_mail import enviar_email

logger = logging.getLogger(__name__)


def verificar_inatividade_usuarios(db: Session) -> dict:
    """
    Cron diário (02:00 UTC):
    - Prestador: 90 dias sem login → força mudança de senha
    - Coletador: 260 dias sem coleta → marca ativo=false
    """
    agora = datetime.utcnow()
    resultados = {
        "prestadores_senha_expirada": 0,
        "coletadores_desativados": 0,
        "emails_enviados": 0,
        "erros": 0
    }

    try:
        # Verificar PRESTADORES: 90 dias sem login (updated_at)
        limite_prestador = agora - timedelta(days=90)
        prestadores_expirados = db.query(User).filter(
            User.is_active == True,
            User.role.name.in_(["prestador", "especialista"]),
            User.updated_at < limite_prestador,
            User.password_expires_at.is_(None)
        ).all()

        for usuario in prestadores_expirados:
            try:
                usuario.password_expires_at = agora
                db.commit()

                assunto = "Ação Requerida: Sua senha expirou"
                corpo = f"""
Sua senha expirou por inatividade (90+ dias sem login).

Por favor, redefina sua senha acessando o sistema.

Data de expiração: {agora.strftime('%d/%m/%Y %H:%M')}
                """.strip()

                enviar_email(usuario.email, assunto, corpo)
                resultados["prestadores_senha_expirada"] += 1
                resultados["emails_enviados"] += 1
            except Exception as e:
                logger.error(f"Erro ao expirar senha prestador {usuario.id}: {e}")
                resultados["erros"] += 1

        # Verificar COLETADORES: 260 dias sem coleta
        limite_coletador = agora - timedelta(days=260)
        coletadores_inativos = db.query(User).filter(
            User.is_active == True,
            User.role.name == "coletador",
            (User.last_coleta_date < limite_coletador) | (User.last_coleta_date.is_(None))
        ).all()

        for usuario in coletadores_inativos:
            try:
                usuario.is_active = False
                usuario.dias_inatividade = 260
                db.commit()

                assunto = "Conta Desativada: Inatividade"
                corpo = f"""
Sua conta foi desativada por inatividade (260+ dias sem coleta).

Contate o administrador para reativar.

Data de desativação: {agora.strftime('%d/%m/%Y %H:%M')}
                """.strip()

                # Email para Master/Admin
                enviar_email("admin@ipcms.com.br", assunto, corpo)
                resultados["coletadores_desativados"] += 1
                resultados["emails_enviados"] += 1
            except Exception as e:
                logger.error(f"Erro ao desativar coletador {usuario.id}: {e}")
                resultados["erros"] += 1

        logger.info(f"Verificação de inatividade concluída: {resultados}")
        return resultados

    except Exception as e:
        logger.error(f"Erro ao verificar inatividade de usuários: {e}", exc_info=True)
        return {**resultados, "erros": 1}
