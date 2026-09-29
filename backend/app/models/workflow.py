"""Workflow engine models for visual workflow builder and execution tracking.

Cérebro MVP Backend: Workflows connect jobs, triggers, and business logic visually.

Models:
- WorkflowDefinition: Immutable definition (nodes, edges, triggers)
- WorkflowExecution: Individual run (status, node results, timeline)

Integration:
- Each node can be a 'job_task' that dispatches to the Job queue
- Triggers watch for events (processo_criado, intimacao_recebida, laudo_concluido, etc.)
- Node results are stored per-execution for audit + debugging

Structure:
- nodes: [{id: "node_1", type: "input|job_task|decision|output", config: {}, inputs: [], outputs: []}, ...]
- edges: [{source: "node_1", target: "node_2"}, ...]
- triggers: [{type: "processo_criado", config: {}}, ...]
- node_results: {node_id: {status: "pending|running|completed|failed", output: {...}, error: "...", started_at: "...", ended_at: "..."}}
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index, ForeignKey
from app.models.types import JSONBType
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class WorkflowDefinition(Base, TimestampMixin):
    """Visual workflow definition (nodes, edges, triggers).

    Attributes:
        id: Primary key
        nome: Workflow name (e.g., "Ofício + Protocolo + Laudo")
        descricao: Human-readable description
        versao: Increment on each update
        nodes: JSONB list of {id, type, config, inputs, outputs}
        edges: JSONB list of {source, target} connections
        triggers: JSONB list of {type, config} event triggers
        ativa: Is this workflow currently active?
        criado_por: Foreign key to user who created it
        executions: Relationship to WorkflowExecution (1-N)
    """
    __tablename__ = "workflow_definition"

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1)

    # Visual structure
    nodes = Column(JSONBType, nullable=False, default=list)
    edges = Column(JSONBType, nullable=False, default=list)
    triggers = Column(JSONBType, nullable=False, default=list)

    # Metadata
    ativa = Column(Boolean, nullable=False, default=True)
    criado_por = Column(Integer)  # FK to user.id (nullable: creator may be deleted)

    # Relationships
    executions = relationship("WorkflowExecution", back_populates="definition", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_workflow_definition_ativa", "ativa"),
        Index("idx_workflow_definition_criado_por", "criado_por"),
    )


class WorkflowExecution(Base, TimestampMixin):
    """Execution instance of a workflow (one run).

    Attributes:
        id: Primary key
        definition_id: FK to WorkflowDefinition
        trigger_event: Type of event that triggered this run (e.g., "processo_criado")
        trigger_id: ID of the entity that triggered (processo_id, intimacao_id, etc.)
        status: "running", "completed", or "failed"
        node_results: JSONB dict {node_id: {status, output, error, timestamps}}
        iniciado_em: When execution started
        concluido_em: When execution finished (NULL if still running)
        definition: Relationship to WorkflowDefinition
    """
    __tablename__ = "workflow_execution"

    id = Column(Integer, primary_key=True)
    definition_id = Column(Integer, ForeignKey("workflow_definition.id", ondelete="CASCADE"), nullable=False)

    # Trigger information
    trigger_event = Column(String(50), nullable=False)
    trigger_id = Column(Integer, nullable=True)

    # Execution state
    status = Column(String(20), nullable=False, default="running")  # running, completed, failed
    node_results = Column(JSONBType, nullable=False, default=dict)  # {node_id: {status, output, error, started_at, ended_at}}

    # Timeline
    iniciado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    concluido_em = Column(DateTime, nullable=True)

    # Relationships
    definition = relationship("WorkflowDefinition", back_populates="executions")

    __table_args__ = (
        Index("idx_workflow_execution_definition", "definition_id"),
        Index("idx_workflow_execution_status", "status"),
        Index("idx_workflow_execution_trigger", "trigger_event", "trigger_id"),
        Index("idx_workflow_execution_iniciado", "iniciado_em"),
    )
