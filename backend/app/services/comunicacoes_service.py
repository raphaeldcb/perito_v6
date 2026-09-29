"""Serviço de gestão de comunicações judiciais por email.

Orquestra processamento de emails via Graph API, classificação de judiciais,
extração de dados processuais, geração de respostas sugeridas e feedback ML.
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.comunicacoes import (
    EmailMessage,
    EmailConfig,
    EmailTemplate,
    EmailFeedback,
    JudicialStatus,
)
from app.schemas.comunicacoes import (
    EmailPainelStatsSchema,
    EmailConfigSchema,
    EmailTemplateSchema,
    EmailMessageSchema,
)
from app.services import graph_mail
from app.services.database import SessionLocal
from app.workers import monitor_emails

logger = logging.getLogger(__name__)


class ComunicacoesService:
    """Service para gestão centralizada de comunicações judiciais."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()

    def obter_painel_stats(self) -> EmailPainelStatsSchema:
        """Retorna estatísticas para o painel principal."""
        hoje = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        recebidos_hoje = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.created_at >= hoje)
            .count()
        )

        judiciais = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.is_judicial == True)
            .count()
        )

        completos = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.status == JudicialStatus.COMPLETO.value)
            .count()
        )

        pendentes = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.status == JudicialStatus.PENDENTE.value)
            .count()
        )

        revisar = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.status == JudicialStatus.REVISAR.value)
            .count()
        )

        respondidos = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.status == JudicialStatus.RESPONDIDO.value)
            .count()
        )

        erros = (
            self.db.query(EmailMessage)
            .filter(EmailMessage.status == JudicialStatus.ERRO.value)
            .count()
        )

        return EmailPainelStatsSchema(
            recebidos_hoje=recebidos_hoje,
            judiciais=judiciais,
            completos=completos,
            pendentes=pendentes,
            revisar=revisar,
            respondidos=respondidos,
            erros=erros,
        )

    def listar_emails(
        self,
        filtros: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[EmailMessageSchema], int]:
        """Lista emails com filtros opcionais.

        Filtros suportados:
        - status: JudicialStatus (str)
        - is_judicial: bool
        - numero_processo: str (LIKE)
        - from_address: str (LIKE)

        Retorna: (lista de EmailMessageSchema, total)
        """
        try:
            query = self.db.query(EmailMessage)

            if filtros:
                if "status" in filtros and filtros["status"]:
                    query = query.filter(EmailMessage.status == filtros["status"])

                if "is_judicial" in filtros and filtros["is_judicial"] is not None:
                    query = query.filter(EmailMessage.is_judicial == filtros["is_judicial"])

                if "numero_processo" in filtros and filtros["numero_processo"]:
                    query = query.filter(
                        EmailMessage.numero_processo.ilike(
                            f"%{filtros['numero_processo']}%"
                        )
                    )

                if "from_address" in filtros and filtros["from_address"]:
                    query = query.filter(
                        EmailMessage.from_address.ilike(f"%{filtros['from_address']}%")
                    )

            total = query.count()

            emails = (
                query.order_by(EmailMessage.received_datetime.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            return (
                [EmailMessageSchema.model_validate(e) for e in emails],
                total,
            )
        except Exception as e:
            logger.error(f"Erro ao listar emails: {e}")
            return [], 0

    def obter_email(self, email_id: int) -> Optional[EmailMessageSchema]:
        """Retorna detalhe de um email específico."""
        try:
            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if email:
                return EmailMessageSchema.model_validate(email)
            return None
        except Exception as e:
            logger.error(f"Erro ao obter email {email_id}: {e}")
            return None

    def obter_config(self) -> Optional[EmailConfigSchema]:
        """Retorna configuração do módulo.

        Se não existir, retorna None. Client pode usar para criar padrão.
        """
        try:
            config = self.db.query(EmailConfig).first()
            if config:
                # Deserializar campos_obrigatorios antes de validar
                if config.campos_obrigatorios and isinstance(config.campos_obrigatorios, str):
                    config.campos_obrigatorios = json.loads(config.campos_obrigatorios)
                return EmailConfigSchema.model_validate(config)
            return None
        except Exception as e:
            logger.error(f"Erro ao obter config: {e}")
            return None

    def salvar_config(self, config_data: Dict[str, Any]) -> EmailConfigSchema:
        """Salva ou atualiza configuração do módulo."""
        try:
            config = self.db.query(EmailConfig).first()

            if not config:
                config = EmailConfig(
                    mailbox_email=config_data.get("mailbox_email", ""),
                    intervalo_minutos=config_data.get("intervalo_minutos", 5),
                    ativo=config_data.get("ativo", True),
                    modo_resposta=config_data.get("modo_resposta", "rascunho"),
                )
                self.db.add(config)
            else:
                config.mailbox_email = config_data.get(
                    "mailbox_email", config.mailbox_email
                )
                config.intervalo_minutos = config_data.get(
                    "intervalo_minutos", config.intervalo_minutos
                )
                config.ativo = config_data.get("ativo", config.ativo)
                config.modo_resposta = config_data.get(
                    "modo_resposta", config.modo_resposta
                )

                if "campos_obrigatorios" in config_data:
                    config.campos_obrigatorios = json.dumps(
                        config_data["campos_obrigatorios"]
                    )

            self.db.commit()

            # Deserializar campos_obrigatorios antes de validar
            if config.campos_obrigatorios and isinstance(config.campos_obrigatorios, str):
                config.campos_obrigatorios = json.loads(config.campos_obrigatorios)

            return EmailConfigSchema.model_validate(config)
        except Exception as e:
            logger.error(f"Erro ao salvar config: {e}")
            self.db.rollback()
            raise

    def listar_templates(self, apenas_ativos: bool = True) -> List[EmailTemplateSchema]:
        """Lista templates de resposta."""
        try:
            query = self.db.query(EmailTemplate)

            if apenas_ativos:
                query = query.filter(EmailTemplate.ativo == True)

            templates = query.order_by(EmailTemplate.nome).all()

            return [EmailTemplateSchema.model_validate(t) for t in templates]
        except Exception as e:
            logger.error(f"Erro ao listar templates: {e}")
            return []

    def criar_template(
        self, nome: str, assunto: str, corpo: str, padrao: bool = False
    ) -> EmailTemplateSchema:
        """Cria novo template de resposta.

        Variáveis suportadas no corpo/assunto:
        - {{tribunal}}
        - {{vara}}
        - {{numero_processo}}
        - {{pedido}}
        - {{assinatura}}
        - {{campos_faltantes}}
        """
        try:
            # Se padrao=True, desabilita outros padrões
            if padrao:
                self.db.query(EmailTemplate).update({"padrao": False})

            template = EmailTemplate(
                nome=nome,
                assunto=assunto,
                corpo=corpo,
                ativo=True,
                padrao=padrao,
            )
            self.db.add(template)
            self.db.commit()

            logger.info(f"✅ Template criado: {nome}")
            return EmailTemplateSchema.model_validate(template)
        except Exception as e:
            logger.error(f"Erro ao criar template: {e}")
            self.db.rollback()
            raise

    def processar_email_manual(self) -> int:
        """Dispara processamento manual da caixa de entrada.

        Reutiliza monitor_emails.processar_caixa_entrada() que:
        1. Lista emails não-lidos do Graph
        2. Extrai CNJ
        3. Salva PDFs
        4. Marca como lido

        Retorna: número de emails processados.
        """
        try:
            if not monitor_emails.configurado():
                logger.warning("Monitor de email DESABILITADO: Graph não configurado")
                return 0

            processados = monitor_emails.processar_caixa_entrada()
            logger.info(f"📧 {processados} emails processados manualmente")
            return processados
        except Exception as e:
            logger.error(f"Erro ao processar email manual: {e}")
            return 0

    def gerar_resposta_dados_incompletos(self, email_id: int) -> Optional[Dict[str, Any]]:
        """Gera resposta automática formal para emails judiciais com dados incompletos.

        Detecta campos faltantes (tribunal, vara, numero_processo, pedido) e gera
        texto formal solicitando os dados necessários para análise.

        Retorna: {
            "tem_campos_faltantes": bool,
            "campos_faltantes": [list de campos],
            "resposta_sugerida": str (texto formal),
            "campos_descricoes": {campo: descrição, ...}
        }
        """
        try:
            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if not email:
                logger.warning(f"Email {email_id} não encontrado")
                return None

            if not email.is_judicial:
                logger.warning(f"Email {email_id} não é judicial")
                return None

            # Campos obrigatórios para judiciais
            campos_obrigatorios = {
                "tribunal": "Tribunal responsável",
                "vara": "Vara/Órgão judiciário",
                "numero_processo": "Número do processo (formato CNJ)",
                "pedido": "Descrição do pedido/intimação"
            }

            # Identifica campos faltantes
            faltantes = []
            for campo, descricao in campos_obrigatorios.items():
                valor = getattr(email, campo, None)
                if not valor or valor.strip() == "":
                    faltantes.append(campo)

            tem_faltantes = len(faltantes) > 0

            # Gera resposta formal
            if tem_faltantes:
                campos_desc = [campos_obrigatorios[c] for c in faltantes]
                campos_lista = "\n".join([f"  • {campos_obrigatorios[c]}" for c in faltantes])

                resposta = f"""Prezados Senhores,

Agradecemos o envio da intimação. Para que possamos prosseguir com a análise e cumprimento do prazo, é necessário que alguns dados sejam fornecidos:

{campos_lista}

Solicitamos que confirme as informações acima para que possamos dar prosseguimento ao procedimento com a máxima celeridade.

Atenciosamente,
IPC Perícias
Tel: +55 67 3042-4300
Email: contato@ipcms.com.br"""
            else:
                resposta = "Todos os dados necessários foram extraídos. Nenhuma resposta automática necessária."

            return {
                "tem_campos_faltantes": tem_faltantes,
                "campos_faltantes": faltantes,
                "resposta_sugerida": resposta,
                "campos_descricoes": {c: campos_obrigatorios[c] for c in faltantes}
            }

        except Exception as e:
            logger.error(f"Erro ao gerar resposta para dados incompletos: {e}")
            return None

    def gerar_resposta_sugerida(
        self, email_id: int, template_id: Optional[int] = None
    ) -> Optional[str]:
        """Gera resposta sugerida para um email.

        Substitui variáveis do template com dados extraídos do email:
        - {{tribunal}} → email.tribunal
        - {{vara}} → email.vara
        - {{numero_processo}} → email.numero_processo
        - {{pedido}} → email.pedido
        - {{assinatura}} → assinatura padrão
        - {{campos_faltantes}} → campos obrigatórios não preenchidos

        Se template_id não informado, usa o template padrão.
        """
        try:
            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if not email:
                logger.warning(f"Email {email_id} não encontrado")
                return None

            # Busca template
            template = None
            if template_id:
                template = (
                    self.db.query(EmailTemplate)
                    .filter(EmailTemplate.id == template_id)
                    .first()
                )
            else:
                # Tenta template padrão, se não tiver usa o primeiro ativo
                template = (
                    self.db.query(EmailTemplate)
                    .filter(
                        and_(EmailTemplate.ativo == True, EmailTemplate.padrao == True)
                    )
                    .first()
                )
                if not template:
                    template = (
                        self.db.query(EmailTemplate)
                        .filter(EmailTemplate.ativo == True)
                        .first()
                    )

            if not template:
                logger.warning("Nenhum template disponível")
                return None

            # Prepara variáveis
            corpo = template.corpo

            # Substitui campos extraídos
            corpo = corpo.replace("{{tribunal}}", email.tribunal or "")
            corpo = corpo.replace("{{vara}}", email.vara or "")
            corpo = corpo.replace("{{numero_processo}}", email.numero_processo or "")
            corpo = corpo.replace("{{pedido}}", email.pedido or "")

            # Assinatura padrão
            assinatura = (
                "\n\nAtenciosamente,\n"
                "IPC Perícias\n"
                "Tel: +55 67 3042-4300\n"
                "Email: contato@ipcms.com.br"
            )
            corpo = corpo.replace("{{assinatura}}", assinatura)

            # Campos faltantes
            config = self.db.query(EmailConfig).first()
            campos_obrigatorios = {}
            if config:
                try:
                    campos_obrigatorios = json.loads(config.campos_obrigatorios)
                except:
                    pass

            faltantes = []
            for campo, obrigatorio in campos_obrigatorios.items():
                if obrigatorio:
                    valor = getattr(email, campo, None)
                    if not valor:
                        faltantes.append(campo)

            campos_faltantes_str = ", ".join(faltantes) if faltantes else "nenhum"
            corpo = corpo.replace("{{campos_faltantes}}", campos_faltantes_str)

            # Salva sugestão no BD
            email.resposta_sugerida = corpo
            email.status = JudicialStatus.REVISAR.value
            email.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"✅ Resposta sugerida gerada para email {email_id}")
            return corpo
        except Exception as e:
            logger.error(f"Erro ao gerar resposta sugerida: {e}")
            self.db.rollback()
            return None

    def salvar_resposta_editada(
        self,
        email_id: int,
        resposta_editada: str,
        campos_corrigidos: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Salva resposta editada pelo usuário e registra feedback.

        Campos_corrigidos é um dict com campos que foram corrigidos:
        {
            "tribunal": {"original": "...", "corrigido": "..."},
            "vara": {...},
            "numero_processo": {...},
            "pedido": {...},
        }

        Registra em EmailFeedback para aprendizado ML.
        """
        try:
            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if not email:
                logger.warning(f"Email {email_id} não encontrado")
                return False

            # Salva resposta no email
            email.resposta_editada = resposta_editada
            email.status = JudicialStatus.COMPLETO.value
            email.updated_at = datetime.utcnow()

            # Registra feedback para aprendizado
            feedback = EmailFeedback(
                email_message_id=email_id,
                resposta_original=email.resposta_sugerida,
                resposta_corrigida=resposta_editada,
            )

            # Mapeia campos corrigidos
            if campos_corrigidos:
                for campo, valores in campos_corrigidos.items():
                    if campo == "tribunal":
                        feedback.tribunal_original = valores.get("original")
                        feedback.tribunal_corrigido = valores.get("corrigido")
                        email.tribunal = valores.get("corrigido")
                    elif campo == "vara":
                        feedback.vara_original = valores.get("original")
                        feedback.vara_corrigida = valores.get("corrigido")
                        email.vara = valores.get("corrigido")
                    elif campo == "comarca":
                        feedback.comarca_original = valores.get("original")
                        feedback.comarca_corrigida = valores.get("corrigido")
                        email.comarca = valores.get("corrigido")
                    elif campo == "numero_processo":
                        feedback.numero_processo_original = valores.get("original")
                        feedback.numero_processo_corrigido = valores.get("corrigido")
                        email.numero_processo = valores.get("corrigido")
                    elif campo == "pedido":
                        feedback.pedido_original = valores.get("original")
                        feedback.pedido_corrigido = valores.get("corrigido")
                        email.pedido = valores.get("corrigido")

            self.db.add(feedback)
            self.db.commit()

            logger.info(f"✅ Resposta salva e feedback registrado para email {email_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar resposta editada: {e}")
            self.db.rollback()
            return False

    def atualizar_status_email(self, email_id: int, novo_status: str) -> bool:
        """Atualiza status de um email.

        Status válidos: NOVO, PROCESSANDO, COMPLETO, PENDENTE, REVISAR,
        RASCUNHO, RESPONDIDO, IGNORADO, ERRO.
        """
        try:
            # Valida status
            try:
                JudicialStatus(novo_status)
            except ValueError:
                logger.error(f"Status inválido: {novo_status}")
                return False

            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if not email:
                logger.warning(f"Email {email_id} não encontrado")
                return False

            email.status = novo_status
            email.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"✅ Status atualizado para {email_id}: {novo_status}")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            self.db.rollback()
            return False

    def extrair_numero_processo(self, texto: str) -> Optional[str]:
        """Extrai número CNJ formatado de um texto.

        Formato esperado: NNNNNNN-DD.AAAA.J.TT.OOOO
        Exemplo: 1234567-89.2023.1.01.0001
        """
        try:
            # Regex CNJ
            cnj_re = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
            match = cnj_re.search(texto)
            if match:
                return match.group(0)
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair número processo: {e}")
            return None

    def marcar_como_lido_graph(self, email_id: int) -> bool:
        """Marca email como lido no Graph.

        Operação best-effort (requer permissão Mail.ReadWrite).
        """
        try:
            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if not email:
                logger.warning(f"Email {email_id} não encontrado")
                return False

            # Chama Graph
            if graph_mail.configurado():
                graph_mail.marcar_lido(email.message_id)
                logger.info(f"✅ Email {email_id} marcado como lido no Graph")
            else:
                logger.warning("Graph não configurado, não é possível marcar como lido")

            return True
        except Exception as e:
            logger.error(f"Erro ao marcar como lido: {e}")
            return False

    def marcar_como_analisado(self, email_id: int) -> bool:
        """Marca email como analisado pelo Perito V6.

        1. Registra timestamp de análise (analyzed_at)
        2. Integra com Graph API para adicionar categoria "ANALISADO PELO PERITO V6" no Outlook
        3. Armazena resposta da API em categories (JSON)

        Retorna: True se sucesso, False se falha.
        """
        try:
            email = self.db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if not email:
                logger.warning(f"Email {email_id} não encontrado")
                return False

            # Marca timestamp
            email.analyzed_at = datetime.utcnow()

            # Tenta adicionar categoria no Outlook via Graph
            if graph_mail.configurado():
                try:
                    # Adiciona categoria no Graph
                    resposta_graph = graph_mail.adicionar_categoria(
                        email.message_id,
                        "ANALISADO PELO PERITO V6"
                    )

                    # Armazena resultado da API
                    if resposta_graph:
                        email.categories = json.dumps({
                            "ANALISADO PELO PERITO V6": resposta_graph,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        logger.info(f"✅ Categoria adicionada no Outlook para email {email_id}")
                    else:
                        logger.warning(f"Graph retornou vazio ao adicionar categoria para {email_id}")
                        # Ainda assim marca localmente mesmo sem sucesso no Outlook
                        email.categories = json.dumps({
                            "status": "falha_graph",
                            "motivo": "Graph API retornou vazio",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                except Exception as e:
                    logger.warning(f"Não foi possível adicionar categoria no Graph: {e}")
                    # Mesmo assim marca como analisado localmente
                    email.categories = json.dumps({
                        "erro": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
            else:
                logger.warning("Graph não configurado, apenas marcando localmente")
                email.categories = json.dumps({
                    "nota": "Graph não configurado",
                    "timestamp": datetime.utcnow().isoformat(),
                })

            self.db.commit()
            logger.info(f"✅ Email {email_id} marcado como ANALISADO PELO PERITO V6 — analyzed_at={email.analyzed_at}")
            return True

        except Exception as e:
            logger.error(f"Erro ao marcar como analisado: {e}")
            self.db.rollback()
            return False
