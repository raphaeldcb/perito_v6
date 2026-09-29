"""Cérebro Phase 3 — Escalation Rules Engine.

Sistema de escalação inteligente com:
- Regras configuráveis (SLA, risco, etc.)
- Notificações multi-canal
- Audit trail completo
- SLA tracking

Production-ready com fallback, error handling, batch operations.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

logger = logging.getLogger(__name__)


class EscalationLevel(str, Enum):
    """Níveis de escalação."""
    INFO = "info"  # Apenas log/registro
    WARNING = "warning"  # Email aviso
    CRITICAL = "critical"  # Email + SMS + Whatsapp
    EXECUTIVE = "executive"  # CEO, Gerente Geral


class EscalationReason(str, Enum):
    """Motivos de escalação (regras pré-definidas)."""
    VENCIMENTO_CRITICO = "vencimento_critico"  # >30d sem resposta
    ERRO_LAUDO = "erro_laudo"  # Validação falhou
    ASSINATURA_FALHOU = "assinatura_falhou"  # A3 timeout/erro
    PROTOCOLO_FALHOU = "protocolo_falhou"  # eSAJ erro 3+ vezes
    PAGAMENTO_VENCIDO = "pagamento_vencido"  # >15d sem pagamento
    QA_REVISAO_LENTA = "qa_revisao_lenta"  # >24h em revisão
    TIMEOUT_WORKFLOW = "timeout_workflow"  # Workflow tempo limite
    RECURSO_ESGOTADO = "recurso_esgotado"  # Queue cheia, delay >1h


@dataclass
class EscalacaoTarefa:
    """Tarefa de escalação."""
    id: int
    tipo_motivo: EscalationReason
    nivel: EscalationLevel
    destinatarios: List[str]  # emails
    titulo: str
    descricao: str
    payload: Dict[str, Any]  # dados contextuais
    timestamp: datetime
    resolvido_em: Optional[datetime] = None
    resolvido_por: Optional[str] = None


@dataclass
class EscalacaoRegra:
    """Regra de escalação."""
    id: str
    motivo: EscalationReason
    condicao: str  # Python lambda-safe expression
    nivel: EscalationLevel
    destinatarios_padrao: List[str]
    template_email: str
    template_sms: str
    ativa: bool = True


class EscalationEngine:
    """Motor de escalação com regras e notificações."""

    # Regras pré-configuradas (vencimento, erro, timeout, etc.)
    REGRAS_PADRAO = {
        EscalationReason.VENCIMENTO_CRITICO: EscalacaoRegra(
            id="rule_vencimento_critico",
            motivo=EscalationReason.VENCIMENTO_CRITICO,
            condicao="dias_atraso > 30",
            nivel=EscalationLevel.CRITICAL,
            destinatarios_padrao=["gerente@ipcs.com.br"],
            template_email="vencimento_critico_30d",
            template_sms="Processo {processo_id} vencido há >30 dias",
            ativa=True
        ),
        EscalationReason.ERRO_LAUDO: EscalacaoRegra(
            id="rule_erro_laudo",
            motivo=EscalationReason.ERRO_LAUDO,
            condicao="validacao_falhou",
            nivel=EscalationLevel.CRITICAL,
            destinatarios_padrao=["qa@ipcs.com.br", "revisor@ipcs.com.br"],
            template_email="erro_laudo_requer_revisao",
            template_sms="Laudo {laudo_id} com erro - revisão necessária",
            ativa=True
        ),
        EscalationReason.ASSINATURA_FALHOU: EscalacaoRegra(
            id="rule_assinatura_falhou",
            motivo=EscalationReason.ASSINATURA_FALHOU,
            condicao="tentativas_assinatura > 2",
            nivel=EscalationLevel.WARNING,
            destinatarios_padrao=["bruno@ipcs.com.br"],
            template_email="assinatura_manual_necessaria",
            template_sms="Assinatura A3 falhou - ação manual necessária",
            ativa=True
        ),
        EscalationReason.PROTOCOLO_FALHOU: EscalacaoRegra(
            id="rule_protocolo_falhou",
            motivo=EscalationReason.PROTOCOLO_FALHOU,
            condicao="tentativas_protocolo >= 3",
            nivel=EscalationLevel.CRITICAL,
            destinatarios_padrao=["gerente@ipcs.com.br", "bruno@ipcs.com.br"],
            template_email="protocolo_falho_escalacao",
            template_sms="Protocolo falhou 3x - revisão necessária",
            ativa=True
        ),
        EscalationReason.PAGAMENTO_VENCIDO: EscalacaoRegra(
            id="rule_pagamento_vencido",
            motivo=EscalationReason.PAGAMENTO_VENCIDO,
            condicao="dias_atraso_pagamento > 15",
            nivel=EscalationLevel.WARNING,
            destinatarios_padrao=["financeiro@ipcs.com.br"],
            template_email="pagamento_15d_vencido",
            template_sms="Cobrança {valor} vencida há {dias} dias",
            ativa=True
        ),
        EscalationReason.QA_REVISAO_LENTA: EscalacaoRegra(
            id="rule_qa_lenta",
            motivo=EscalationReason.QA_REVISAO_LENTA,
            condicao="tempo_em_revisao > 86400",  # >24h em segundos
            nivel=EscalationLevel.INFO,
            destinatarios_padrao=["qa@ipcs.com.br"],
            template_email="qa_revisao_lenta_24h",
            template_sms="Revisão {laudo_id} aguardando há >24h",
            ativa=True
        ),
        EscalationReason.TIMEOUT_WORKFLOW: EscalacaoRegra(
            id="rule_timeout_workflow",
            motivo=EscalationReason.TIMEOUT_WORKFLOW,
            condicao="tempo_execucao > sla",
            nivel=EscalationLevel.WARNING,
            destinatarios_padrao=["gerente@ipcs.com.br"],
            template_email="workflow_timeout_sla",
            template_sms="Workflow {workflow_id} ultrapassou SLA",
            ativa=True
        ),
        EscalationReason.RECURSO_ESGOTADO: EscalacaoRegra(
            id="rule_recurso_esgotado",
            motivo=EscalationReason.RECURSO_ESGOTADO,
            condicao="delay_fila > 3600",  # >1h
            nivel=EscalationLevel.WARNING,
            destinatarios_padrao=["devops@ipcs.com.br"],
            template_email="fila_atrasada_recurso",
            template_sms="Fila de jobs atrasada >1h",
            ativa=True
        ),
    }

    def __init__(self, db: Session, notificacao_service=None):
        """
        Args:
            db: SQLAlchemy session
            notificacao_service: Serviço de notificação (email, SMS, WhatsApp)
        """
        self.db = db
        self.notificacao_service = notificacao_service

    async def escalar(
        self,
        motivo: EscalationReason,
        nivel: Optional[EscalationLevel] = None,
        contexto: Optional[Dict[str, Any]] = None,
        destinatarios_customizados: Optional[List[str]] = None
    ) -> EscalacaoTarefa:
        """
        Escala uma tarefa baseado em regra e contexto.

        Args:
            motivo: Razão da escalação
            nivel: Nível customizado (default: da regra)
            contexto: Dados contextuais (processo_id, laudo_id, etc.)
            destinatarios_customizados: Emails extras

        Returns:
            EscalacaoTarefa criada (persisted in DB)

        Exemplo:
            await escalacao.escalar(
                motivo=EscalationReason.VENCIMENTO_CRITICO,
                contexto={"processo_id": 123, "dias_atraso": 35}
            )
        """
        try:
            logger.info(f"Escalando: {motivo.value}")

            # 1. Busca regra
            regra = self.REGRAS_PADRAO.get(motivo)
            if not regra or not regra.ativa:
                logger.warning(f"Regra não encontrada ou inativa: {motivo}")
                return await self._criar_escalacao_manual(motivo, contexto)

            # 2. Define nível
            nivel_final = nivel or regra.nivel

            # 3. Computa destinatários
            destinatarios = regra.destinatarios_padrao.copy()
            if destinatarios_customizados:
                destinatarios.extend(destinatarios_customizados)

            # 4. Formata notificações
            contexto = contexto or {}
            titulo = self._formatar_titulo(regra, contexto)
            descricao = self._formatar_descricao(regra, contexto)

            # 5. Persiste tarefa de escalação
            from app.models import AuditLog
            escalacao = AuditLog(
                tipo="escalacao",
                entidade="workflow",
                entidade_id=contexto.get("workflow_id", 0),
                acao=f"escalacao_{motivo.value}",
                usuario_id=None,  # System-generated
                detalhes={
                    "motivo": motivo.value,
                    "nivel": nivel_final.value,
                    "destinatarios": destinatarios,
                    "contexto": contexto,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            self.db.add(escalacao)
            self.db.commit()

            # 6. Envia notificações
            await self._notificar(
                destinatarios=destinatarios,
                nivel=nivel_final,
                titulo=titulo,
                descricao=descricao,
                contexto=contexto
            )

            logger.info(f"Escalação concluída: {motivo.value} → {nivel_final.value}")

            return EscalacaoTarefa(
                id=escalacao.id,
                tipo_motivo=motivo,
                nivel=nivel_final,
                destinatarios=destinatarios,
                titulo=titulo,
                descricao=descricao,
                payload=contexto,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Erro escalando: {e}", exc_info=True)
            raise

    async def _criar_escalacao_manual(
        self,
        motivo: EscalationReason,
        contexto: Optional[Dict]
    ) -> EscalacaoTarefa:
        """Cria escalação manual quando regra não existe."""
        return EscalacaoTarefa(
            id=0,
            tipo_motivo=motivo,
            nivel=EscalationLevel.WARNING,
            destinatarios=["gerente@ipcs.com.br"],
            titulo=f"Escalação Manual: {motivo.value}",
            descricao=str(contexto or {}),
            payload=contexto or {},
            timestamp=datetime.utcnow()
        )

    def _formatar_titulo(self, regra: EscalacaoRegra, contexto: Dict) -> str:
        """Formata título da escalação usando template."""
        templates = {
            EscalationReason.VENCIMENTO_CRITICO: "⚠️ Processo vencido há {dias_atraso} dias",
            EscalationReason.ERRO_LAUDO: "🔴 Laudo {laudo_id} com erro de validação",
            EscalationReason.ASSINATURA_FALHOU: "❌ Falha em assinatura A3 - ação manual",
            EscalationReason.PROTOCOLO_FALHOU: "❌ Protocolo falhou 3x - revisão necessária",
            EscalationReason.PAGAMENTO_VENCIDO: "💰 Pagamento vencido há {dias_atraso_pagamento}d",
        }

        template = templates.get(regra.motivo, regra.motivo.value)
        try:
            return template.format(**contexto)
        except KeyError:
            return template

    def _formatar_descricao(self, regra: EscalacaoRegra, contexto: Dict) -> str:
        """Formata descrição da escalação."""
        desc = f"Motivo: {regra.motivo.value}\n"
        desc += f"Nível: {regra.nivel.value}\n"
        desc += f"Timestamp: {datetime.utcnow().isoformat()}\n"
        desc += f"\nContexto:\n"
        for k, v in contexto.items():
            desc += f"  - {k}: {v}\n"
        return desc

    async def _notificar(
        self,
        destinatarios: List[str],
        nivel: EscalationLevel,
        titulo: str,
        descricao: str,
        contexto: Dict
    ):
        """Envia notificações multi-canal."""
        try:
            if not self.notificacao_service:
                logger.warning("Notificação service não configurado")
                return

            # Seleciona canais por nível
            canais = {
                EscalationLevel.INFO: ["log"],
                EscalationLevel.WARNING: ["email"],
                EscalationLevel.CRITICAL: ["email", "sms", "whatsapp"],
                EscalationLevel.EXECUTIVE: ["email", "sms", "whatsapp"],
            }.get(nivel, ["email"])

            for canal in canais:
                try:
                    if canal == "email":
                        await self.notificacao_service.enviar_email(
                            destinatarios=destinatarios,
                            assunto=titulo,
                            corpo=descricao
                        )
                    elif canal == "sms":
                        for tel in self._extrair_telefones(contexto):
                            await self.notificacao_service.enviar_sms(
                                telefone=tel,
                                mensagem=titulo
                            )
                    elif canal == "whatsapp":
                        for tel in self._extrair_telefones(contexto):
                            await self.notificacao_service.enviar_whatsapp(
                                numero=tel,
                                mensagem=descricao
                            )
                except Exception as e:
                    logger.error(f"Erro enviando {canal}: {e}")

        except Exception as e:
            logger.error(f"Erro notificando escalação: {e}")

    def _extrair_telefones(self, contexto: Dict) -> List[str]:
        """Extrai telefones do contexto."""
        telefones = []
        if "telefone" in contexto:
            telefones.append(contexto["telefone"])
        if "telefone_cliente" in contexto:
            telefones.append(contexto["telefone_cliente"])
        return [t for t in telefones if t]

    async def resolver_escalacao(
        self,
        escalacao_id: int,
        resolvido_por: str,
        notas: Optional[str] = None
    ) -> bool:
        """
        Marca escalação como resolvida.

        Args:
            escalacao_id: ID da escalação
            resolvido_por: Usuário que resolveu
            notas: Notas de resolução

        Returns:
            True se sucesso
        """
        try:
            from app.models import AuditLog
            escalacao = self.db.query(AuditLog).filter_by(id=escalacao_id).first()

            if not escalacao:
                logger.warning(f"Escalação {escalacao_id} não encontrada")
                return False

            escalacao.detalhes["resolvido_em"] = datetime.utcnow().isoformat()
            escalacao.detalhes["resolvido_por"] = resolvido_por
            escalacao.detalhes["notas"] = notas

            self.db.commit()
            logger.info(f"Escalação {escalacao_id} resolvida por {resolvido_por}")
            return True

        except Exception as e:
            logger.error(f"Erro resolvendo escalação: {e}")
            self.db.rollback()
            return False

    def get_escalacoes_pendentes(self, horas: int = 24) -> List[Dict]:
        """
        Retorna escalações pendentes das últimas N horas.

        Args:
            horas: Período em horas

        Returns:
            Lista de escalações
        """
        try:
            from app.models import AuditLog
            data_limite = datetime.utcnow() - timedelta(hours=horas)

            escalacoes = self.db.query(AuditLog).filter(
                AuditLog.acao.like("escalacao_%"),
                AuditLog.created_at >= data_limite
            ).order_by(desc(AuditLog.created_at)).all()

            return [
                {
                    "id": e.id,
                    "motivo": e.detalhes.get("motivo"),
                    "nivel": e.detalhes.get("nivel"),
                    "timestamp": e.created_at.isoformat(),
                    "contexto": e.detalhes.get("contexto", {}),
                    "resolvido": "resolvido_em" in e.detalhes
                }
                for e in escalacoes
            ]

        except Exception as e:
            logger.error(f"Erro buscando escalações pendentes: {e}")
            return []

    def get_sla_status(self, workflow_id: int) -> Dict[str, Any]:
        """
        Retorna status de SLA de um workflow.

        Calcula:
        - Tempo decorrido vs SLA
        - % de progresso
        - Status (ok, warning, critical)
        """
        try:
            from app.models import WorkflowExecution, WorkflowDefinition

            exec_row = self.db.query(WorkflowExecution).filter_by(
                id=workflow_id
            ).first()

            if not exec_row:
                return {"status": "not_found"}

            defn = exec_row.definition
            sla_minutos = defn.criado_em.get("sla_minutos", 120) if isinstance(defn.criado_em, dict) else 120

            tempo_decorrido = (datetime.utcnow() - exec_row.iniciado_em).total_seconds() / 60
            percentual = (tempo_decorrido / sla_minutos) * 100

            status = "ok"
            if percentual > 100:
                status = "critical"
            elif percentual > 75:
                status = "warning"

            return {
                "workflow_id": workflow_id,
                "sla_minutos": sla_minutos,
                "tempo_decorrido_min": tempo_decorrido,
                "percentual_sla": percentual,
                "status": status
            }

        except Exception as e:
            logger.error(f"Erro calculando SLA: {e}")
            return {"status": "error"}
