# v6/backend/app/modules/ferramentas/{tool}/service.py
"""Cerebro (IA Coordination) — Business logic and services."""
import logging
import asyncio
import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================================
# Workflow Templates & Builder (from cerebro_advanced.py)
# ============================================================================

class WorkflowTemplates:
    """Predefined workflow templates."""

    @staticmethod
    def get_template_by_type(tipo: str) -> Optional[Dict[str, Any]]:
        """Retorna template de workflow por tipo.

        Tipos suportados:
        - processo_criado
        - intimacao_recebida
        - laudo_pronto
        - etc.
        """
        templates = {
            "processo_criado": {
                "nome": "Processo Criado → Ofício → Protocolo",
                "descricao": "Workflow padrão para novo processo",
                "versao": 1,
                "nodes": [
                    {"id": "inicio", "tipo": "start"},
                    {"id": "validar", "tipo": "validate_processo"},
                    {"id": "gerar_oficio", "tipo": "gerar_oficio"},
                    {"id": "protocolo", "tipo": "protocolo"},
                    {"id": "fim", "tipo": "end"}
                ],
                "edges": [
                    {"from": "inicio", "to": "validar"},
                    {"from": "validar", "to": "gerar_oficio"},
                    {"from": "gerar_oficio", "to": "protocolo"},
                    {"from": "protocolo", "to": "fim"}
                ],
                "triggers": ["processo.criado"],
                "sla_minutos": 120
            },
            "intimacao_recebida": {
                "nome": "Intimação Recebida → Análise → Resposta",
                "descricao": "Workflow para intimações recebidas",
                "versao": 1,
                "nodes": [
                    {"id": "inicio", "tipo": "start"},
                    {"id": "analisar", "tipo": "analisar_intimacao"},
                    {"id": "generar_resposta", "tipo": "gerar_resposta"},
                    {"id": "notificar", "tipo": "notificar_responsavel"},
                    {"id": "fim", "tipo": "end"}
                ],
                "edges": [
                    {"from": "inicio", "to": "analisar"},
                    {"from": "analisar", "to": "generar_resposta"},
                    {"from": "generar_resposta", "to": "notificar"},
                    {"from": "notificar", "to": "fim"}
                ],
                "triggers": ["intimacao.recebida"],
                "sla_minutos": 1440  # 24 horas
            },
            "laudo_pronto": {
                "nome": "Laudo Pronto → Protocolo",
                "descricao": "Workflow para laudos prontos",
                "versao": 1,
                "nodes": [
                    {"id": "inicio", "tipo": "start"},
                    {"id": "validar_laudo", "tipo": "validar_laudo"},
                    {"id": "assinador", "tipo": "assinador_laudo"},
                    {"id": "protocolo", "tipo": "protocolo_laudo"},
                    {"id": "fim", "tipo": "end"}
                ],
                "edges": [
                    {"from": "inicio", "to": "validar_laudo"},
                    {"from": "validar_laudo", "to": "assinador"},
                    {"from": "assinador", "to": "protocolo"},
                    {"from": "protocolo", "to": "fim"}
                ],
                "triggers": ["laudo.pronto"],
                "sla_minutos": 480  # 8 horas
            }
        }
        return templates.get(tipo)


class WorkflowBuilder:
    """Builder para workflows customizados."""

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.triggers = []
        self.sla_minutos = 120

    def add_node(self, node_id: str, node_type: str) -> "WorkflowBuilder":
        """Adiciona nó ao workflow."""
        self.nodes.append({"id": node_id, "tipo": node_type})
        return self

    def add_edge(self, from_id: str, to_id: str) -> "WorkflowBuilder":
        """Adiciona aresta ao workflow."""
        self.edges.append({"from": from_id, "to": to_id})
        return self

    def add_trigger(self, trigger: str) -> "WorkflowBuilder":
        """Adiciona trigger."""
        self.triggers.append(trigger)
        return self

    def set_sla(self, minutos: int) -> "WorkflowBuilder":
        """Define SLA."""
        self.sla_minutos = minutos
        return self

    def build(self) -> Dict[str, Any]:
        """Constrói workflow."""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "triggers": self.triggers,
            "sla_minutos": self.sla_minutos
        }


# ============================================================================
# Event Classification (from cerebro.py)
# ============================================================================

async def classify_event_pattern(
    evento_tipo: str,
    evento_origem: str,
    db: Session,
    user_id: int
) -> Optional[int]:
    """Classifica evento e encontra/cria padrão correspondente.

    Tenta:
    1. Qwen (com timeout 5s)
    2. Fallback: classificação local simples
    3. Retorna padrão_id ou None
    """
    try:
        from app.models.cerebro import PadrãoRAG

        # Simple local classification (v0.1 MVP)
        # TODO: Integrar Qwen (fase 2)

        # Find or create pattern
        padrão = db.query(PadrãoRAG).filter(
            PadrãoRAG.usuario_id == user_id,
            PadrãoRAG.tipo == evento_tipo,
            PadrãoRAG.origem == evento_origem
        ).first()

        if padrão:
            padrão.frequency += 1
            padrão.recalc_score()
        else:
            padrão = PadrãoRAG(
                usuario_id=user_id,
                owner_id=user_id,
                dominio="operacional",  # Default (será refino com Qwen)
                tipo=evento_tipo,
                descricao=f"Padrão de {evento_tipo} via {evento_origem}",
                frequency=1,
                aceitos=0,
                score=0.5
            )
            db.add(padrão)

        db.flush()
        return padrão.id

    except Exception as e:
        logger.warning(f"[WARN] classify_event_pattern erro: {e}")
        return None


# ============================================================================
# Workflow Execution (from cerebro_advanced.py)
# ============================================================================

async def executar_workflow_async(execution_id: int, db_url: str):
    """Executa workflow em background."""
    try:
        logger.info(f"Executando workflow: {execution_id}")
        # TODO: Implementar lógica de execução (usar cerebro_engine.py)
        # await CerebroEngine(db).executar(execution_id)
    except Exception as e:
        logger.error(f"Erro executando workflow: {e}")


async def executar_batch_async(
    batch_id: str,
    workflow_id: int,
    processo_ids: List[int],
    paralelizar: int,
    db_url: str
):
    """Executa batch de workflows em paralelo."""
    try:
        logger.info(f"Executando batch: {batch_id} com {len(processo_ids)} processos")
        # TODO: Implementar lógica de batch com asyncio.gather
    except Exception as e:
        logger.error(f"Erro executando batch: {e}")


# ============================================================================
# Escalation Engine (from cerebro_advanced.py)
# ============================================================================

class EscalationEngine:
    """Motor de escalações."""

    def __init__(self, db: Session):
        self.db = db

    async def resolver_escalacao(
        self,
        escalacao_id: int,
        resolvido_por: str,
        notas: str
    ) -> bool:
        """Marca escalação como resolvida."""
        try:
            from app.models import AuditLog

            escalacao = self.db.query(AuditLog).filter_by(id=escalacao_id).first()
            if not escalacao:
                return False

            detalhes = escalacao.detalhes or {}
            detalhes["resolvido_em"] = datetime.utcnow().isoformat()
            detalhes["resolvido_por"] = resolvido_por
            detalhes["notas"] = notas
            escalacao.detalhes = detalhes

            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Erro resolvendo escalação: {e}")
            return False


class EscalationReason:
    """Razões de escalação."""
    VENCIMENTO_CRITICO = "vencimento_critico"
    PRAZO_EXCEDIDO = "prazo_excedido"
    ERRO_SISTEMA = "erro_sistema"
    INTERVENCAO_MANUAL = "intervencao_manual"
