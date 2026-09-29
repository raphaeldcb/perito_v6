"""Pydantic schemas for workflow API (request/response validation)."""
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class WorkflowNode(BaseModel):
    """A single node in the workflow DAG.

    Types (MVP — see workflow_compiler.SUPPORTED_EXECUTABLE_TYPES):
    - input: Structural. Receives trigger data, no Job dispatched.
    - job_task: Dispatches a Job to the queue (config.job_type -> Job.tipo).
    - output: Structural. Marks the end of the flow, no Job dispatched.
    - decision: Accepted by the schema (so drafts can be saved), but rejected
      at /execute time — conditional branching isn't implemented yet.

    inputs: maps Job payload keys -> value source. Each value is either:
      - "ref:trigger"            -> the execute request's trigger_id
      - "ref:trigger.<field>"    -> a key from the execute request's payload
      - "ref:<node_id>.output.<field>" -> a field from that upstream job_task
        node's Job.resultado (node_id MUST be this node's single job_task
        predecessor per the edges list — MVP has no fan-in)
      - anything else -> used as a literal value
    outputs: declarative list of field names this node's Job.resultado is
      expected to produce (purely documentation/canvas metadata; not
      enforced server-side).
    """
    id: str
    type: str  # input, job_task, decision, output
    config: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)  # output field names (docs only)


class WorkflowEdge(BaseModel):
    """A connection between two nodes."""
    source: str
    target: str


class WorkflowTrigger(BaseModel):
    """An event that can trigger this workflow."""
    type: str  # processo_criado, intimacao_recebida, laudo_concluido, etc.
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionCreate(BaseModel):
    """Request to create a new workflow."""
    nome: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    triggers: List[WorkflowTrigger]

    @validator('nodes')
    def validate_nodes_not_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Workflow deve ter pelo menos 1 nó")
        return v

    @validator('edges')
    def validate_edges_reference_valid_nodes(cls, v, values):
        # Validator para edges que referencia 'nodes' (que já foi validado)
        if 'nodes' not in values:
            return v
        node_ids = {n.id for n in values['nodes']}
        for edge in v:
            if edge.source not in node_ids:
                raise ValueError(f"Edge referencia nó source inexistente: '{edge.source}'")
            if edge.target not in node_ids:
                raise ValueError(f"Edge referencia nó target inexistente: '{edge.target}'")
        return v


class WorkflowDefinitionUpdate(BaseModel):
    """Request to update a workflow."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    nodes: Optional[List[WorkflowNode]] = None
    edges: Optional[List[WorkflowEdge]] = None
    triggers: Optional[List[WorkflowTrigger]] = None
    ativa: Optional[bool] = None


class WorkflowDefinitionResponse(BaseModel):
    """Response with full workflow definition."""
    id: int
    nome: str
    descricao: Optional[str]
    versao: int
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    triggers: List[WorkflowTrigger]
    ativa: bool
    criado_por: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NodeResult(BaseModel):
    """Result of a single node execution."""
    status: str  # pending, running, completed, failed
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class WorkflowExecutionResponse(BaseModel):
    """Response with workflow execution status and results."""
    id: int
    definition_id: int
    trigger_event: str
    trigger_id: Optional[int]
    status: str  # running, completed, failed
    node_results: Dict[str, NodeResult]
    iniciado_em: datetime
    concluido_em: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow (manual trigger)."""
    trigger_event: str = Field(default="manual")
    trigger_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None  # Additional context data


class WorkflowNodeTypeSchema(BaseModel):
    """Metadata for available node types."""
    type: str
    description: str
    inputs_schema: Dict[str, Any]  # JSON schema for inputs
    outputs_schema: Dict[str, Any]  # JSON schema for outputs
    config_schema: Optional[Dict[str, Any]] = None  # JSON schema for config


class WorkflowNodeTypesResponse(BaseModel):
    """List of available node types."""
    node_types: List[WorkflowNodeTypeSchema]
