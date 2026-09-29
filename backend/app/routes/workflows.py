"""Routes for visual workflow builder and execution API.

Endpoints:
- GET  /api/v1/workflows/nodes/types        → Introspect available node types
- POST /api/v1/workflows                    → Create new workflow definition
- GET  /api/v1/workflows                    → List all workflows (paginated)
- GET  /api/v1/workflows/{id}               → Fetch one workflow
- PUT  /api/v1/workflows/{id}               → Update workflow
- POST /api/v1/workflows/{id}/execute       → Trigger execution
- GET  /api/v1/workflows/{id}/executions/{exec_id} → Fetch execution status + results
- DELETE /api/v1/workflows/{id}             → Delete workflow

Integration with Job Queue:
- Nodes with type='job_task' create Job entries (config.job_type → Job.tipo)
- Job.workflow_execution_id links back to the execution for audit
- Triggers automatically dispatch workflows when events fire
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.middleware import get_current_user
from app.models import User, WorkflowDefinition, WorkflowExecution
from app.services import get_db
from app.services import workflow_engine
from app.services.workflow_compiler import WorkflowValidationError
from app.services.job_types import JOB_TYPE_REGISTRY
from app.schemas.workflow import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowDefinitionResponse,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse,
    WorkflowNodeTypesResponse,
    WorkflowNodeTypeSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["workflows"])


# ===== Node Type Introspection =====
#
# Structural node types (input/output) + one job_task entry per real Job.tipo
# handled by the executor (app/routes/jobs.py::_aplicar_resultado + mac_agent).
# `decision` is listed as "supported: false" — accepted by the schema so a
# draft can be saved, but /execute rejects it (no branching engine yet).

_STRUCTURAL_NODE_TYPES = [
    WorkflowNodeTypeSchema(
        type="input",
        description="Nó estrutural: representa o disparo do workflow (trigger_id / payload). Não cria Job.",
        inputs_schema={},
        outputs_schema={"trigger_id": {"type": "integer"}, "payload": {"type": "object"}},
    ),
    WorkflowNodeTypeSchema(
        type="output",
        description="Nó estrutural: marca o fim do fluxo. Não cria Job.",
        inputs_schema={},
        outputs_schema={},
    ),
    WorkflowNodeTypeSchema(
        type="decision",
        description="Branch condicional — AINDA NÃO SUPORTADO. Aceito no schema, rejeitado em /execute.",
        inputs_schema={"data": {"type": "object"}},
        outputs_schema={"branch": {"type": "string"}},
        config_schema={"supported": False},
    ),
]


def _build_node_types() -> list[WorkflowNodeTypeSchema]:
    node_types = list(_STRUCTURAL_NODE_TYPES)
    for job_type in JOB_TYPE_REGISTRY:
        node_types.append(
            WorkflowNodeTypeSchema(
                type="job_task",
                description=f"[{job_type['tipo']}] {job_type['label']} — {job_type['description']}",
                inputs_schema={k: {"type": "any"} for k in job_type["expected_inputs"]},
                outputs_schema={k: {"type": "any"} for k in job_type["expected_outputs"]},
                config_schema={"job_type": job_type["tipo"]},
            )
        )
    return node_types


@router.get("/workflows/nodes/types", response_model=WorkflowNodeTypesResponse)
async def get_node_types(user: User = Depends(get_current_user)):
    """Introspect available node types for visual builder.

    Retorna os nós estruturais (input/output/decision) + 1 entrada `job_task`
    por tipo de Job real que a fila (app/routes/jobs.py + mac_agent) sabe
    processar — ver app/services/job_types.py (fonte única desses tipos).
    """
    return WorkflowNodeTypesResponse(node_types=_build_node_types())


# ===== CRUD Operations =====

@router.post("/workflows", response_model=WorkflowDefinitionResponse)
async def create_workflow(
    request: WorkflowDefinitionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new workflow definition.

    Body:
    {
        "nome": "Ofício + Protocolo",
        "descricao": "...",
        "nodes": [...],
        "edges": [...],
        "triggers": [...]
    }
    """
    workflow = WorkflowDefinition(
        nome=request.nome,
        descricao=request.descricao,
        nodes=[node.dict() for node in request.nodes],
        edges=[edge.dict() for edge in request.edges],
        triggers=[trigger.dict() for trigger in request.triggers],
        ativa=True,
        criado_por=user.id,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    logger.info(f"Workflow '{workflow.nome}' (id={workflow.id}) created by user {user.id}")
    return workflow


@router.get("/workflows", response_model=dict)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    ativa: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all workflows (paginated).

    Query params:
    - skip: Offset (default 0)
    - limit: Limit (default 20, max 100)
    - ativa: Filter by active status (optional)
    """
    q = db.query(WorkflowDefinition)

    if ativa is not None:
        q = q.filter(WorkflowDefinition.ativa == ativa)

    total = q.count()
    workflows = q.order_by(desc(WorkflowDefinition.created_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "workflows": [WorkflowDefinitionResponse.from_orm(w).dict() for w in workflows],
    }


@router.get("/workflows/{workflow_id}", response_model=WorkflowDefinitionResponse)
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch a single workflow definition."""
    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/workflows/{workflow_id}", response_model=WorkflowDefinitionResponse)
async def update_workflow(
    workflow_id: int,
    request: WorkflowDefinitionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a workflow definition (increments versao).

    Only updates non-null fields. Creates new version.
    """
    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Only creator or admin can update (TODO: add permission check)
    if workflow.criado_por != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this workflow")

    # Update fields
    if request.nome is not None:
        workflow.nome = request.nome
    if request.descricao is not None:
        workflow.descricao = request.descricao
    if request.nodes is not None:
        workflow.nodes = [node.dict() for node in request.nodes]
    if request.edges is not None:
        workflow.edges = [edge.dict() for edge in request.edges]
    if request.triggers is not None:
        workflow.triggers = [trigger.dict() for trigger in request.triggers]
    if request.ativa is not None:
        workflow.ativa = request.ativa

    workflow.versao += 1
    db.commit()
    db.refresh(workflow)
    logger.info(f"Workflow {workflow_id} updated to versao {workflow.versao}")
    return workflow


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a workflow (cascades to executions)."""
    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.criado_por != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this workflow")

    db.delete(workflow)
    db.commit()
    logger.info(f"Workflow {workflow_id} deleted")
    return {"status": "deleted", "workflow_id": workflow_id}


# ===== Execution Management =====

@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: int,
    request: WorkflowExecuteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger a workflow execution.

    Body:
    {
        "trigger_event": "processo_criado",  (default: "manual")
        "trigger_id": 123,  (optional — usado por inputs "ref:trigger")
        "payload": {...}  (optional — usado por inputs "ref:trigger.<field>")
    }

    Valida o DAG PRIMEIRO (ciclos/tipos/fan-in) ANTES de criar a execution.
    Se a validação falhar, retorna erro 400 SEM deixar execution órfã.
    Depois compila e cria os Jobs (raízes com status "na_fila", nós
    dependentes com `aguardar_job_id` apontando pro Job predecessor — a fila
    só os libera quando a dependência conclui). Retorna a execução recém
    criada com status "running" e o node_results inicial.
    """
    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not workflow.ativa:
        raise HTTPException(status_code=400, detail="Workflow is inactive")

    # FIX #4: Validar DAG ANTES de criar execution (evita orphaned executions)
    try:
        from app.services.workflow_compiler import WorkflowCompiler
        compiler = WorkflowCompiler(workflow.nodes, workflow.edges)
        compiler.validate()
    except WorkflowValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Só agora cria a execution
    execution = WorkflowExecution(
        definition_id=workflow_id,
        trigger_event=request.trigger_event,
        trigger_id=request.trigger_id,
        status="running",
        node_results={},
        iniciado_em=datetime.utcnow(),
    )
    db.add(execution)
    db.flush()  # precisa do execution.id antes de criar os Jobs

    try:
        workflow_engine.dispatch_workflow(
            db, workflow, execution, request.trigger_id, request.payload
        )
    except WorkflowValidationError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(execution)
    logger.info(f"Workflow {workflow_id} execution {execution.id} started (trigger: {request.trigger_event})")
    return execution


@router.get("/workflows/{workflow_id}/executions/{exec_id}", response_model=WorkflowExecutionResponse)
async def get_execution(
    workflow_id: int,
    exec_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch execution status and node results.

    Useful for polling progress of running workflows.
    """
    execution = (
        db.query(WorkflowExecution)
        .filter(
            WorkflowExecution.id == exec_id,
            WorkflowExecution.definition_id == workflow_id,
        )
        .first()
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/workflows/{workflow_id}/executions", response_model=dict)
async def list_executions(
    workflow_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List executions of a workflow (paginated).

    Query params:
    - skip: Offset (default 0)
    - limit: Limit (default 20, max 100)
    - status: Filter by status (running, completed, failed) — optional
    """
    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    q = db.query(WorkflowExecution).filter(WorkflowExecution.definition_id == workflow_id)

    if status is not None:
        q = q.filter(WorkflowExecution.status == status)

    total = q.count()
    executions = q.order_by(desc(WorkflowExecution.iniciado_em)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "executions": [WorkflowExecutionResponse.from_orm(e).dict() for e in executions],
    }
