"""Cérebro Phase 2 — Triggers Avançados.

Tipos de triggers:
- Temporal (cron-based): "todo dia às 8h"
- Event-based: "processo vencido", "intimação recebida"
- Webhook: integração com sistemas externos
- Manual: acionamento manual via UI

Cada trigger monitora e dispara WorkflowExecution quando condição é atendida.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
import croniter
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import WorkflowDefinition, WorkflowExecution, Process, Intimacao

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Tipos de trigger suportados."""
    TEMPORAL = "temporal"
    EVENT_BASED = "event_based"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    DATA_CHANGE = "data_change"


@dataclass
class TriggerConfig:
    """Configuração de um trigger."""
    type: TriggerType
    enabled: bool = True
    description: str = ""
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class TemporalTrigger:
    """Trigger baseado em tempo (cron)."""

    def __init__(self, cron_expression: str, timezone: str = "UTC"):
        """
        Args:
            cron_expression: ex: "0 8 * * *" (diariamente às 8h)
            timezone: timezone para interpretação
        """
        self.cron_expression = cron_expression
        self.timezone = timezone
        self.cron = croniter.croniter(cron_expression)

    def should_trigger(self, last_checked: Optional[datetime] = None) -> bool:
        """Verifica se trigger deve disparar."""
        now = datetime.utcnow()

        if last_checked is None:
            # Primeira execução
            return True

        # Verifica se próxima ocorrência está no passado (já passou)
        next_occurrence = self.cron.get_next(datetime)
        return next_occurrence <= now

    def next_trigger_time(self) -> datetime:
        """Retorna próximo tempo de disparo."""
        return self.cron.get_next(datetime)


class EventBasedTrigger:
    """Trigger baseado em eventos do sistema."""

    EVENT_TYPES = {
        "process_created": "Processo criado",
        "process_deadline_approaching": "Prazo de processo próximo",
        "process_overdue": "Processo vencido",
        "intimacao_received": "Intimação recebida",
        "intimacao_deadline_approaching": "Prazo de intimação próximo",
        "laudo_generated": "Laudo gerado",
        "job_completed": "Job completado",
        "job_failed": "Job falhou",
        "custom_event": "Evento customizado",
    }

    def __init__(
        self,
        event_type: str,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            event_type: tipo de evento a monitorar
            filters: filtros adicionais (ex: {area: "engenharia", status: "ativo"})
        """
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Evento inválido: {event_type}")

        self.event_type = event_type
        self.filters = filters or {}

    def matches(self, db: Session, event_data: Dict[str, Any]) -> bool:
        """Verifica se evento corresponde aos critérios."""
        # Validação básica de tipo
        if event_data.get("event_type") != self.event_type:
            return False

        # Validar filtros
        for key, expected_value in self.filters.items():
            actual_value = event_data.get(key)
            if actual_value != expected_value:
                return False

        return True

    def get_trigger_payload(
        self, db: Session, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extrai payload do evento para usar em inputs do workflow."""
        return {
            "event_type": self.event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }


class WebhookTrigger:
    """Trigger acionado via webhook (POST HTTP)."""

    def __init__(
        self,
        webhook_path: str,
        secret_token: Optional[str] = None,
        verify_signature: bool = True,
    ):
        """
        Args:
            webhook_path: path do webhook (ex: /webhooks/workflows/123)
            secret_token: token para validar requisição
            verify_signature: se deve validar assinatura HMAC
        """
        self.webhook_path = webhook_path
        self.secret_token = secret_token or str(uuid.uuid4())
        self.verify_signature = verify_signature

    def validate_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """Valida assinatura HMAC da requisição."""
        if not self.verify_signature:
            return True

        import hmac
        import hashlib

        signature = headers.get("X-Webhook-Signature")
        if not signature:
            return False

        expected_signature = hmac.new(
            self.secret_token.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class ManualTrigger:
    """Trigger acionado manualmente via UI/API."""

    def __init__(self, description: str = ""):
        self.description = description
        self.last_triggered: Optional[datetime] = None

    def trigger_now(self) -> bool:
        """Aciona trigger manualmente."""
        self.last_triggered = datetime.utcnow()
        return True


class TriggerRegistry:
    """Registro de triggers e monitoramento."""

    def __init__(self, db: Session):
        self.db = db
        self.active_triggers: Dict[int, List[TriggerConfig]] = {}
        # workflow_id → [triggers]

    def register_workflow_triggers(
        self,
        workflow_id: int,
        triggers: List[Dict[str, Any]],
    ) -> None:
        """Registra triggers de um workflow."""
        trigger_configs = []

        for trigger_def in triggers:
            trigger_type = TriggerType(trigger_def.get("type", "manual"))

            config = TriggerConfig(
                type=trigger_type,
                enabled=trigger_def.get("enabled", True),
                description=trigger_def.get("description", ""),
                config=trigger_def.get("config", {}),
            )
            trigger_configs.append(config)

        self.active_triggers[workflow_id] = trigger_configs

    def check_temporal_triggers(self) -> List[Tuple[int, Dict[str, Any]]]:
        """Verifica triggers temporais.

        Returns:
            [(workflow_id, trigger_config), ...]
        """
        results = []

        for workflow_id, triggers in self.active_triggers.items():
            for trigger_config in triggers:
                if (
                    trigger_config.type != TriggerType.TEMPORAL
                    or not trigger_config.enabled
                ):
                    continue

                try:
                    cron_expr = trigger_config.config.get("cron_expression")
                    if not cron_expr:
                        continue

                    temporal_trigger = TemporalTrigger(cron_expr)
                    last_checked = trigger_config.config.get("last_checked")
                    if last_checked:
                        last_checked = datetime.fromisoformat(last_checked)

                    if temporal_trigger.should_trigger(last_checked):
                        # Atualizar last_checked
                        trigger_config.config["last_checked"] = (
                            datetime.utcnow().isoformat()
                        )
                        results.append((workflow_id, trigger_config))

                except Exception as e:
                    logger.error(
                        f"Erro ao verificar temporal trigger {workflow_id}: {e}"
                    )

        return results

    def check_event_triggers(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> List[Tuple[int, Dict[str, Any], Dict[str, Any]]]:
        """Verifica triggers baseados em eventos.

        Returns:
            [(workflow_id, trigger_config, trigger_payload), ...]
        """
        results = []

        for workflow_id, triggers in self.active_triggers.items():
            for trigger_config in triggers:
                if (
                    trigger_config.type != TriggerType.EVENT_BASED
                    or not trigger_config.enabled
                ):
                    continue

                try:
                    event_trigger = EventBasedTrigger(
                        event_type=trigger_config.config.get("event_type"),
                        filters=trigger_config.config.get("filters"),
                    )

                    if event_trigger.matches(self.db, event_data):
                        payload = event_trigger.get_trigger_payload(
                            self.db, event_data
                        )
                        results.append((workflow_id, trigger_config, payload))

                except Exception as e:
                    logger.error(
                        f"Erro ao verificar event trigger {workflow_id}: {e}"
                    )

        return results


class TriggerMonitor:
    """Monitor de triggers (roda em background)."""

    def __init__(self, db: Session):
        self.db = db
        self.registry = TriggerRegistry(db)
        self._load_workflows()

    def _load_workflows(self) -> None:
        """Carrega workflows ativos e seus triggers."""
        workflows = (
            self.db.query(WorkflowDefinition)
            .filter(WorkflowDefinition.ativa == True)
            .all()
        )

        for workflow in workflows:
            if workflow.triggers:
                self.registry.register_workflow_triggers(
                    workflow.id, workflow.triggers
                )

    def check_all_triggers(self) -> Dict[str, List]:
        """Verifica todos os triggers.

        Returns:
            {
                "temporal": [(workflow_id, trigger_config), ...],
                "event_based": [(workflow_id, trigger_config, payload), ...],
            }
        """
        results = {
            "temporal": self.registry.check_temporal_triggers(),
            "event_based": [],
        }

        return results

    def dispatch_workflow_from_trigger(
        self,
        workflow_id: int,
        trigger_event: str,
        trigger_id: Optional[int] = None,
        trigger_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Dispara execução de workflow a partir de um trigger.

        Returns:
            execution_id ou None se falha
        """
        try:
            workflow = self.db.query(WorkflowDefinition).get(workflow_id)
            if not workflow or not workflow.ativa:
                logger.warning(f"Workflow {workflow_id} inativo")
                return None

            execution = WorkflowExecution(
                definition_id=workflow_id,
                trigger_event=trigger_event,
                trigger_id=trigger_id,
                status="queued",
            )
            self.db.add(execution)
            self.db.flush()

            logger.info(
                f"Workflow {workflow_id} disparado por {trigger_event} "
                f"(execution {execution.id})"
            )

            return execution.id

        except Exception as e:
            logger.error(
                f"Erro ao disparar workflow {workflow_id}: {e}"
            )
            return None

    def process_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> List[int]:
        """Processa evento e dispara workflows correspondentes.

        Returns:
            [execution_id, ...]
        """
        execution_ids = []

        # Verificar triggers event-based
        matches = self.registry.check_event_triggers(event_type, event_data)

        for workflow_id, trigger_config, trigger_payload in matches:
            exec_id = self.dispatch_workflow_from_trigger(
                workflow_id,
                trigger_event=event_type,
                trigger_id=event_data.get("id"),
                trigger_payload=trigger_payload,
            )
            if exec_id:
                execution_ids.append(exec_id)

        return execution_ids

    def emit_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> List[int]:
        """Emite evento e dispara workflows.

        Args:
            event_type: "created", "updated", "deleted"
            entity_type: "process", "intimacao", "laudo"
            entity_id: ID da entidade
            details: dados adicionais

        Returns:
            [execution_id, ...]
        """
        event_data = {
            "event_type": f"{entity_type}_{event_type}",
            "id": entity_id,
            "entity_type": entity_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if details:
            event_data.update(details)

        return self.process_event(f"{entity_type}_{event_type}", event_data)


# ============================================================================
# Helpers para eventos comuns
# ============================================================================

def create_process_overdue_event(
    db: Session,
    process_id: int,
    days_overdue: int,
) -> Dict[str, Any]:
    """Cria evento de processo vencido."""
    process = db.query(Process).get(process_id)

    return {
        "event_type": "process_overdue",
        "id": process_id,
        "numero_processo": getattr(process, "numero_processo", None),
        "days_overdue": days_overdue,
        "deadline": getattr(process, "deadline", None).isoformat()
        if getattr(process, "deadline", None)
        else None,
    }


def create_intimacao_received_event(
    db: Session,
    intimacao_id: int,
) -> Dict[str, Any]:
    """Cria evento de intimação recebida."""
    intimacao = db.query(Intimacao).get(intimacao_id)

    return {
        "event_type": "intimacao_received",
        "id": intimacao_id,
        "process_id": getattr(intimacao, "process_id", None),
        "deadline": getattr(intimacao, "deadline", None).isoformat()
        if getattr(intimacao, "deadline", None)
        else None,
    }
