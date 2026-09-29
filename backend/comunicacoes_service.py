"""Serviço para monitoramento de comunicações judiciais via Microsoft Graph.

Busca emails da caixa postal, classifica como judicial ou não, extrai dados
processuais e armazena no banco de dados para acompanhamento via UI.

Reutiliza:
  - graph_mail.py (Microsoft Graph API)
  - JudicialClassificationService (classificação compartilhada com Intimacao)

Modelo: ComunicacaoMensagem
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    ComunicacaoConfig,
    ComunicacaoMensagem,
    ComunicacaoDadosProcessuais,
    ComunicacaoLog,
)
from app.services import graph_mail
from app.services.judicial_classification import JudicialClassificationService

logger = logging.getLogger(__name__)


class ComunicacoesJudiciaisService:
    """Service para processar comunicações judiciais de email."""

    def __init__(self, db: Session):
        self.db = db

    def obter_config(self, conta_email: str = "financeiro@ipcms.com.br") -> ComunicacaoConfig:
        """Obtém ou cria configuração para a conta de email."""
        config = self.db.query(ComunicacaoConfig).filter_by(
            conta_email=conta_email
        ).first()

        if not config:
            config = ComunicacaoConfig(
                conta_email=conta_email,
                intervalo_minutos=5,
                ativo=True,
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)

        return config

    def buscar_emails_nao_processados(self, limite: int = 50) -> list[dict]:
        """Busca emails não-lidos via Microsoft Graph."""
        try:
            if not graph_mail.configurado():
                logger.warning("Microsoft Graph não configurado")
                return []

            emails = graph_mail.listar_nao_lidos(limite=limite)
            logger.info(f"📧 {len(emails)} emails não-lidos encontrados")
            return emails

        except Exception as e:
            logger.error(f"Erro buscando emails: {e}")
            return []

    def _classificar_judicial(self, texto: str) -> tuple[bool, Decimal]:
        """Classifica se é email judicial usando serviço compartilhado.

        Delega para JudicialClassificationService para reutilizar com Intimacao.
        """
        eh_judicial, confianca = JudicialClassificationService.classificar(texto)
        return eh_judicial, confianca

    def _extrair_dados_processuais(self, texto: str) -> dict:
        """Extrai dados processuais usando serviço compartilhado."""
        return JudicialClassificationService.extrair_dados_processuais(texto)

    def processar_mensagem(
        self,
        external_id: str,
        remetente: str,
        email_remetente: str,
        assunto: str,
        corpo: str,
        data_recebimento: datetime,
        attachments: Optional[list] = None,
    ) -> Optional[ComunicacaoMensagem]:
        """Processa um email e armazena como comunicação."""
        try:
            # Verificar se já foi processada (idempotência)
            existente = self.db.query(ComunicacaoMensagem).filter_by(
                external_id=external_id
            ).first()

            if existente:
                logger.debug(f"Email {external_id} já processado")
                return existente

            # Classificar como judicial
            texto_completo = f"{assunto}\n{corpo}"
            eh_judicial, confianca = self._classificar_judicial(texto_completo)

            # Extrair dados processuais
            dados_processuais = self._extrair_dados_processuais(texto_completo)

            # Criar mensagem
            mensagem = ComunicacaoMensagem(
                external_id=external_id,
                remetente=remetente[:255],
                email_remetente=email_remetente[:255],
                assunto=assunto[:1000] if assunto else "Sem assunto",
                corpo=corpo,
                data_recebimento=data_recebimento,
                eh_judicial=eh_judicial,
                confianca_ia=confianca,
                status="NOVO",
            )

            self.db.add(mensagem)
            self.db.flush()

            # Adicionar dados processuais se encontrados
            if dados_processuais.get("numero_processo"):
                dados_msg = ComunicacaoDadosProcessuais(
                    mensagem_id=mensagem.id,
                    numero_processo=dados_processuais["numero_processo"],
                    vara=dados_processuais.get("vara"),
                    comarca=dados_processuais.get("comarca"),
                    tribunal=dados_processuais.get("tribunal"),
                    campo_obrigatorio_faltante=None,
                )
                self.db.add(dados_msg)

            self.db.commit()
            self.db.refresh(mensagem)

            logger.info(
                f"📧 Email processado: {external_id[:20]}... "
                f"judicial={eh_judicial} processo={dados_processuais.get('numero_processo')}"
            )

            return mensagem

        except Exception as e:
            logger.error(f"Erro processando email {external_id}: {e}")
            self.db.rollback()
            return None

    def registrar_log(
        self,
        config_id: int,
        operacao: str,
        nivel: str,
        mensagem: str,
        dados: Optional[dict] = None,
    ) -> None:
        """Registra log de operação."""
        try:
            log = ComunicacaoLog(
                config_id=config_id,
                operacao=operacao,
                nivel=nivel,
                mensagem=mensagem[:1000],
                dados=dados or {},
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro registrando log: {e}")
            self.db.rollback()
