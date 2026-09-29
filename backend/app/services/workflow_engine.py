"""Executa workflows compilados, reaproveitando a fila de Jobs existente.

Não é um scheduler paralelo: usa o MESMO mecanismo de dependência que já
existe em `routes/jobs.py` (`payload["aguardar_job_id"]` -> `/jobs/proximo`
só entrega o job quando a dependência está `concluido`). Isso é o padrão que
já roda em produção para `protocolo_laudo` esperando `gerar_laudo`.

Fluxo:
1. `dispatch_workflow()` (chamado em POST /workflows/{id}/execute):
   - valida o DAG (WorkflowCompiler)
   - cria 1 Job por nó `job_task`, em ordem topológica
   - nós sem predecessor job_task entram direto na fila ("na_fila")
   - nós com 1 predecessor job_task entram com `aguardar_job_id` apontando
     pro Job do predecessor, e ficam com placeholders para inputs que vêm
     do output do nó anterior (`_workflow_pending_refs`)
   - grava um snapshot em `WorkflowExecution.node_results`

2. `advance_on_job_complete()` (chamado em PATCH /jobs/{id}/concluir, DEPOIS
   de `_aplicar_resultado` e ANTES do commit final — mesma transação):
   - atualiza o node_results do nó correspondente
   - se o job terminou com sucesso, resolve os `_workflow_pending_refs` dos
     jobs filhos diretos (mesma execução, `aguardar_job_id == job.id`) com
     os valores reais de `job.resultado`
   - recalcula `WorkflowExecution.status` (running -> completed/failed)
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import Job, WorkflowDefinition, WorkflowExecution
from app.services.workflow_compiler import WorkflowCompiler, WorkflowValidationError

logger = logging.getLogger(__name__)

# Job.status terminais (definidos em routes/jobs.py::concluir_job)
JOB_STATUS_SUCCESS = "concluido"
JOB_STATUS_FAILED = "erro"


def dispatch_workflow(
    db: Session,
    workflow: WorkflowDefinition,
    execution: WorkflowExecution,
    trigger_id: Optional[int],
    trigger_payload: Optional[Dict[str, Any]],
) -> None:
    """Compila e dispara a primeira leva de Jobs de uma execução.

    Levanta WorkflowValidationError se o DAG for inválido — o caller (rota)
    deve traduzir isso em HTTP 400 e NÃO deve ter criado a execução ainda
    (validar antes de db.add(execution), ver routes/workflows.py).
    """
    compiler = WorkflowCompiler(workflow.nodes, workflow.edges)
    compiler.validate()
    order = compiler.topological_order()

    job_by_node: Dict[str, Job] = {}
    node_results: Dict[str, Any] = {}

    for node_id in order:
        node = compiler.nodes[node_id]
        node_type = node.get("type")

        if node_type != "job_task":
            # Nós estruturais (input/output) não disparam Job.
            node_results[node_id] = {
                "status": "concluido",
                "job_id": None,
                "output": None,
                "error": None,
                "started_at": datetime.utcnow().isoformat(),
                "ended_at": datetime.utcnow().isoformat(),
            }
            continue

        # FIX #3: Suportar múltiplos predecessores (fan-in)
        pred_node_ids = compiler.job_predecessors(node_id)
        payload, pending_refs = _resolve_inputs(
            node, pred_node_ids, trigger_id, trigger_payload
        )
        payload["_workflow_node_id"] = node_id
        payload["_workflow_execution_id"] = execution.id
        if pending_refs:
            payload["_workflow_pending_refs"] = pending_refs
        if pred_node_ids:
            pred_jobs = [job_by_node[pred_id] for pred_id in pred_node_ids]
            payload["_workflow_aguardar_job_ids"] = [j.id for j in pred_jobs]
            # Compatibilidade: primeira dependência no campo antigo (se houver)
            if len(pred_jobs) > 0:
                payload["aguardar_job_id"] = pred_jobs[0].id

        job = Job(
            tipo=node["config"]["job_type"],
            payload=payload,
            status="na_fila",
            workflow_execution_id=execution.id,
        )
        db.add(job)
        db.flush()  # precisa do job.id pra referenciar como aguardar_job_id / node seguinte
        job_by_node[node_id] = job

        node_results[node_id] = {
            "status": job.status,
            "job_id": job.id,
            "output": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": None,
        }
        logger.info(
            "Workflow %s exec %s: job %s (tipo=%s) criado para node %s%s",
            workflow.id, execution.id, job.id, job.tipo, node_id,
            # `pred_node_ids` (plural) — a versão singular sobrou do tempo em que
            # o MVP só aceitava 1 predecessor e levantava NameError em TODO
            # job_task disparado, derrubando o POST /execute com 500.
            f" (aguarda jobs {payload['_workflow_aguardar_job_ids']})" if pred_node_ids else "",
        )

    execution.node_results = node_results


def advance_on_job_complete(db: Session, job: Job) -> None:
    """Propaga o resultado de um Job pertencente a um workflow.

    Chamado de dentro de routes/jobs.py::concluir_job logo após
    `job.status` ser atualizado (concluido/erro/na_fila-retry), na MESMA
    transação (antes do commit final), pra evitar qualquer janela em que um
    job filho seja reivindicado com payload ainda não resolvido.
    """
    if not job.workflow_execution_id:
        return

    execution = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == job.workflow_execution_id
    ).first()
    if not execution:
        logger.warning("Job %s referencia workflow_execution %s inexistente", job.id, job.workflow_execution_id)
        return

    node_id = (job.payload or {}).get("_workflow_node_id")
    if not node_id:
        return

    node_results = dict(execution.node_results or {})
    entry = dict(node_results.get(node_id, {}))
    entry["status"] = job.status
    entry["job_id"] = job.id
    entry["error"] = job.erro
    if job.status in (JOB_STATUS_SUCCESS, JOB_STATUS_FAILED):
        entry["ended_at"] = datetime.utcnow().isoformat()
    if job.status == JOB_STATUS_SUCCESS:
        entry["output"] = job.resultado
    node_results[node_id] = entry
    execution.node_results = node_results

    if job.status == JOB_STATUS_SUCCESS:
        _resolve_children(db, execution, job, node_id)

    _recompute_execution_status(execution)


def _resolve_children(db: Session, execution: WorkflowExecution, job: Job, completed_node_id: str) -> None:
    """Preenche os inputs pendentes (`ref:node.output.field`) dos Jobs
    filhos diretos deste job, agora que temos `job.resultado` real.

    FIX #7: Single query com filtro em vez de loop (evita N+1 queries).
    FIX #3: Suporta fan-in — resolve child only if ALL predecessors completed.
    """
    # Query única: pega apenas jobs filhos que aguardam THIS job
    children = db.query(Job).filter(
        Job.workflow_execution_id == execution.id,
        Job.status == "na_fila",
        Job.payload["aguardar_job_id"].astext == str(job.id),
    ).all()

    resultado = job.resultado or {}
    workflow_def = execution.definition
    # Rebuild compiler para verificar predecessores
    from app.services.workflow_compiler import WorkflowCompiler
    compiler = WorkflowCompiler(workflow_def.nodes, workflow_def.edges)

    for child in children:
        payload = dict(child.payload or {})
        node_id = payload.get("_workflow_node_id")
        if not node_id:
            continue

        # FIX #3: Verificar se TODOS os predecessores completaram
        pred_node_ids = compiler.job_predecessors(node_id)
        node_results = dict(execution.node_results or {})
        all_preds_done = True
        for pred_id in pred_node_ids:
            pred_result = node_results.get(pred_id, {})
            if pred_result.get("status") != JOB_STATUS_SUCCESS:
                all_preds_done = False
                break

        if not all_preds_done:
            # Ainda não liberamos — aguardar outros predecessores
            continue

        pending = payload.pop("_workflow_pending_refs", None)
        if not pending:
            continue
        # Resolve os refs de uma vez (não loop)
        for key, ref in pending.items():
            field = ref.get("field")
            payload[key] = resultado.get(field) if field else resultado
        child.payload = payload
        db.add(child)
        logger.info("Job %s (workflow exec %s): inputs resolvidos a partir do job %s (fan-in: all preds done)", child.id, execution.id, job.id)


def _recompute_execution_status(execution: WorkflowExecution) -> None:
    statuses = [
        v.get("status") for v in (execution.node_results or {}).values()
        if v.get("job_id") is not None  # ignora nós estruturais (input/output)
    ]
    if any(s == JOB_STATUS_FAILED for s in statuses):
        execution.status = "failed"
        execution.concluido_em = execution.concluido_em or datetime.utcnow()
    elif statuses and all(s == JOB_STATUS_SUCCESS for s in statuses):
        execution.status = "completed"
        execution.concluido_em = execution.concluido_em or datetime.utcnow()
    else:
        execution.status = "running"


def _resolve_inputs(
    node: Dict[str, Any],
    pred_node_ids: Optional[list[str]] | Optional[str],  # FIX #3: suporta list ou str (compat)
    trigger_id: Optional[int],
    trigger_payload: Optional[Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve node['inputs'] em (payload_pronto, pending_refs).

    pending_refs fica vazio se todos os inputs já puderam ser resolvidos
    de imediato (trigger ou literal).

    FIX #3: Suporta múltiplos predecessores (pred_node_ids é list).
    Se for str (compatibilidade), converte para list.
    """
    # Normalizar: str → list
    if isinstance(pred_node_ids, str):
        pred_node_ids = [pred_node_ids]
    elif pred_node_ids is None:
        pred_node_ids = []

    payload: Dict[str, Any] = {}
    pending: Dict[str, Any] = {}
    trigger_payload = trigger_payload or {}

    for key, val in (node.get("inputs") or {}).items():
        if isinstance(val, str) and val.startswith("ref:"):
            ref = val[len("ref:"):]

            if ref == "trigger":
                payload[key] = trigger_id
            elif ref.startswith("trigger."):
                payload[key] = trigger_payload.get(ref[len("trigger."):])
            else:
                # ref:<node_id>.output.<field> ou ref:<node_id>.<field>
                parts = ref.split(".")
                source_node_id = parts[0]
                if source_node_id not in pred_node_ids:
                    raise WorkflowValidationError(
                        f"Input '{key}' referencia '{source_node_id}' mas não é "
                        f"um predecessor direto. Predecessores: {pred_node_ids}"
                    )
                field = parts[-1] if len(parts) > 1 else None
                pending[key] = {"node_id": source_node_id, "field": field}
        else:
            payload[key] = val

    return payload, pending
