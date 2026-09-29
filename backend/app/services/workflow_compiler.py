"""Compilador de workflows visuais (DAG nodes+edges) → validação estrutural.

Responsabilidade única: garantir que um WorkflowDefinition é executável antes
de qualquer Job ser criado. A execução em si (mapeamento de outputs → inputs,
disparo de Jobs) fica em `app/services/workflow_engine.py`, que reaproveita o
mecanismo de dependência que a fila de Jobs já tem (`payload.aguardar_job_id`,
ver `routes/jobs.py::proximo_job`) em vez de reinventar um scheduler.

Regras do MVP (documentadas para não surpreender quem for estender depois):
- Cada nó `job_task` pode depender de, no máximo, 1 nó `job_task` upstream
  (fan-in não suportado ainda — a fila só entende 1 `aguardar_job_id`).
- Nós `decision` (branching condicional) não são executáveis ainda — a
  validação rejeita o workflow com um erro claro em vez de ignorar o nó.
- Nós `input`/`output` são estruturais (não disparam Job); servem só para
  documentar entrada/saída do fluxo no canvas.
"""
from typing import List, Dict, Any

from app.services.job_types import is_valid_job_type

SUPPORTED_EXECUTABLE_TYPES = {"input", "job_task", "output"}
UNSUPPORTED_TYPES = {"decision"}  # aceito no schema, rejeitado na compilação (MVP)


class WorkflowValidationError(ValueError):
    """Erro de validação estrutural do DAG (ciclo, nó órfão, fan-in, etc.)."""


class WorkflowCompiler:
    """Valida e ordena topologicamente um DAG de workflow (nodes + edges)."""

    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self.nodes: Dict[str, Dict[str, Any]] = {n["id"]: n for n in nodes}
        if len(self.nodes) != len(nodes):
            raise WorkflowValidationError("IDs de nós duplicados no workflow")

        self.graph: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        self.reverse_graph: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            if src not in self.nodes or tgt not in self.nodes:
                raise WorkflowValidationError(
                    f"Edge referencia nó inexistente: {src} → {tgt}"
                )
            self.graph[src].append(tgt)
            self.reverse_graph[tgt].append(src)

    def validate(self) -> None:
        """Roda todas as validações. Levanta WorkflowValidationError se algo falhar."""
        self._validate_node_types()
        self._validate_no_cycles()
        # FIX #3: Remover _validate_single_dependency — agora suportamos fan-in

    def _validate_node_types(self) -> None:
        for node_id, node in self.nodes.items():
            node_type = node.get("type")
            if node_type in UNSUPPORTED_TYPES:
                raise WorkflowValidationError(
                    f"Nó '{node_id}' é do tipo '{node_type}', que ainda não é "
                    "executável nesta versão do Cérebro (MVP suporta apenas "
                    "cadeias lineares de job_task)."
                )
            if node_type not in SUPPORTED_EXECUTABLE_TYPES:
                raise WorkflowValidationError(
                    f"Nó '{node_id}' tem tipo desconhecido: '{node_type}'"
                )
            if node_type == "job_task":
                job_type = (node.get("config") or {}).get("job_type")
                if not job_type:
                    raise WorkflowValidationError(
                        f"Nó '{node_id}' (job_task) não tem config.job_type definido"
                    )
                if not is_valid_job_type(job_type):
                    raise WorkflowValidationError(
                        f"Nó '{node_id}': job_type '{job_type}' não é reconhecido "
                        "(ver app/services/job_types.py::JOB_TYPE_REGISTRY)"
                    )

    def _validate_no_cycles(self) -> None:
        visited: set = set()
        rec_stack: set = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in self.graph.get(node_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited and has_cycle(node_id):
                raise WorkflowValidationError("Workflow contém um ciclo (não é um DAG válido)")

    def topological_order(self) -> List[str]:
        """Ordena nós (dependências primeiro). Assume validate() já rodou."""
        visited: set = set()
        order: List[str] = []

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            for pred in self.reverse_graph.get(node_id, []):
                visit(pred)
            order.append(node_id)

        for node_id in self.nodes:
            visit(node_id)
        return order

    def job_predecessor(self, node_id: str) -> str | None:
        """Retorna o primeiro nó job_task predecessor direto (ou None).
        Mantido por compatibilidade; usar job_predecessors() para fan-in."""
        preds = self.job_predecessors(node_id)
        return preds[0] if preds else None

    def job_predecessors(self, node_id: str) -> List[str]:
        """FIX #3: Retorna TODOS os nós job_task predecessores diretos
        (suporta fan-in). Ordena por ID para determinismo."""
        preds = [
            p for p in self.reverse_graph.get(node_id, [])
            if self.nodes[p].get("type") == "job_task"
        ]
        return sorted(preds)  # Ordena por ID para determinismo
