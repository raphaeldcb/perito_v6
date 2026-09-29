"""Cérebro — Workflow Templates (6 pré-construídos, TODOS executáveis).

Estes templates são o conteúdo semeado em `workflow_definition` por
`scripts/seed_ferramentas_cerebro.py`. Eles precisam obedecer ao MESMO
contrato que a API, o motor e o canvas usam — não é documentação solta:

- `nodes[].type`  ∈ {input, job_task, output}
  (`decision`/`integration` NÃO são executáveis — ver workflow_compiler.py)
- `nodes[].config.job_type` de todo `job_task` tem que existir em
  `app/services/job_types.py::JOB_TYPE_REGISTRY` (é o que a fila sabe rodar)
- `nodes[].inputs` é um **DICT** {chave_do_payload: valor|"ref:..."}:
    "ref:trigger"                  -> trigger_id da requisição
    "ref:trigger.<campo>"          -> campo do payload da requisição
    "ref:<node_id>.output.<campo>" -> campo do Job.resultado de um
                                      predecessor job_task DIRETO
  (`workflow_engine._resolve_inputs` faz `.items()` nisso)
- `nodes[].outputs` é a lista de **nomes de campo** de `Job.resultado`
  (documental) — NÃO node_ids. A topologia mora exclusivamente em `edges`.

Histórico: até 08/2026 estes templates gravavam `inputs`/`outputs` como
listas de node_ids (duplicando as edges). Resultado: `GET /api/v1/workflows`
devolvia 500 (pydantic recusava lista onde o schema pede dict) e
`POST /execute` era impossível (nós `decision`/`integration` + sem job_type).
Travado por `tests/test_workflows_seed_contract.py`.

Regra da casa: nada de fake. Onde não existe job type real (WhatsApp, JIRA,
Kanban, e-mail), o nó foi REMOVIDO em vez de virar enfeite que quebra no
/execute.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Tipos de workflow pré-construídos."""
    PROCESSO_CRIADO = "processo_criado"
    INTIMACAO_RECEBIDA = "intimacao_recebida"
    LAUDO_PRONTO = "laudo_pronto"
    PAGAMENTO_VENCIDO = "pagamento_vencido"
    VENCIMENTO_CRITICO = "vencimento_critico"
    ERRO_LAUDO = "erro_laudo"


class WorkflowPhase(str, Enum):
    """Fases de execução de workflow."""
    TRIGGER = "trigger"
    ANALYSIS = "analysis"
    DECISION = "decision"
    EXECUTION = "execution"
    NOTIFICATION = "notification"
    ROLLBACK = "rollback"


@dataclass
class WorkflowNode:
    """Nó de workflow — espelha `app/schemas/workflow.py::WorkflowNode`.

    `inputs` é dict {chave_do_payload: valor|"ref:..."} e `outputs` é lista de
    nomes de campo de Job.resultado. Ligação entre nós é feita por `edges`.
    """
    id: str
    type: str  # "input", "job_task", "output"
    config: Dict[str, Any]
    inputs: Dict[str, Any] = None  # {payload_key: valor | "ref:..."}
    outputs: List[str] = None  # nomes de campo de Job.resultado

    def __post_init__(self):
        if self.inputs is None:
            self.inputs = {}
        if self.outputs is None:
            self.outputs = []


class WorkflowTemplates:
    """Biblioteca de workflows pré-construídos (production-ready)."""

    @staticmethod
    def processo_criado() -> Dict[str, Any]:
        """Processo novo → baixa os autos no eSAJ → extrai texto → indexa no RAG.

        Os 3 job_task existem de verdade na fila (`esaj_sincronizar`,
        `converter_pdf`, `indexar_rag`), então o /execute roda ponta a ponta.

        O template antigo prometia "análise de risco → ofício → protocolo", mas
        não existe job type para gerar ofício — era decoração. Foi trocado pelo
        que a fila realmente faz e que alimenta o RAG do acervo.
        """
        return {
            "id": "tmpl_processo_criado",
            "nome": "Processo Criado → Autos → Indexação RAG",
            "descricao": (
                "Novo processo: baixa os autos no eSAJ, extrai o texto do PDF e "
                "indexa no RAG para busca semântica."
            ),
            "versao": 1,
            "tipo": WorkflowType.PROCESSO_CRIADO.value,
            "sla_minutos": 120,
            "nodes": [
                {
                    "id": "trigger_processo",
                    "type": "input",
                    "config": {"event": "processo.criado"},
                    "inputs": {},
                    "outputs": [],
                },
                {
                    "id": "baixar_autos",
                    "type": "job_task",
                    "config": {"job_type": "esaj_sincronizar"},
                    "inputs": {"numero_cnj": "ref:trigger.numero_cnj"},
                    "outputs": ["pdf_path"],
                },
                {
                    "id": "extrair_texto",
                    "type": "job_task",
                    "config": {"job_type": "converter_pdf"},
                    "inputs": {"pdf_path": "ref:baixar_autos.output.pdf_path"},
                    "outputs": ["texto"],
                },
                {
                    "id": "indexar_acervo",
                    "type": "job_task",
                    "config": {"job_type": "indexar_rag"},
                    "inputs": {
                        "origem": "processo",
                        "ref_id": "ref:trigger",
                        "texto": "ref:extrair_texto.output.texto",
                    },
                    "outputs": [],
                },
                {
                    "id": "fim",
                    "type": "output",
                    "config": {"status": "completed"},
                    "inputs": {},
                    "outputs": [],
                },
            ],
            "edges": [
                {"source": "trigger_processo", "target": "baixar_autos"},
                {"source": "baixar_autos", "target": "extrair_texto"},
                {"source": "extrair_texto", "target": "indexar_acervo"},
                {"source": "indexar_acervo", "target": "fim"},
            ],
            "triggers": [
                {
                    "type": "processo.criado",
                    "config": {
                        "payload_schema": {
                            "processo_id": "int",
                            "numero_cnj": "string",
                        }
                    },
                }
            ],
        }

    @staticmethod
    def intimacao_recebida() -> Dict[str, Any]:
        """Intimação nova → análise IA (Qwen) → interpretação da decisão.

        `analise_ia` grava os dados extraídos na Intimacao (integrado=True) e
        `interpretar_decisao` produz a leitura do que foi decidido. O cálculo de
        prazo/alerta não virou nó porque não existe job type para isso — roda
        pelo `_aplicar_resultado` de `analise_ia`, não pela fila.
        """
        return {
            "id": "tmpl_intimacao_recebida",
            "nome": "Intimação Recebida → Análise IA → Interpretação",
            "descricao": (
                "Intimação nova: extrai dados com o Qwen local e interpreta a "
                "decisão para alimentar prazo e providências."
            ),
            "versao": 1,
            "tipo": WorkflowType.INTIMACAO_RECEBIDA.value,
            "sla_minutos": 5,
            "nodes": [
                {
                    "id": "trigger_intimacao",
                    "type": "input",
                    "config": {"event": "intimacao.recebida"},
                    "inputs": {},
                    "outputs": [],
                },
                {
                    "id": "analisa_intimacao",
                    "type": "job_task",
                    "config": {"job_type": "analise_ia"},
                    "inputs": {"intimacao_id": "ref:trigger"},
                    "outputs": ["dados"],
                },
                {
                    "id": "interpreta_decisao",
                    "type": "job_task",
                    "config": {"job_type": "interpretar_decisao"},
                    "inputs": {"intimacao_id": "ref:trigger"},
                    "outputs": ["interpretacao"],
                },
                {
                    "id": "fim",
                    "type": "output",
                    "config": {"status": "completed"},
                    "inputs": {},
                    "outputs": [],
                },
            ],
            "edges": [
                {"source": "trigger_intimacao", "target": "analisa_intimacao"},
                {"source": "analisa_intimacao", "target": "interpreta_decisao"},
                {"source": "interpreta_decisao", "target": "fim"},
            ],
            "triggers": [
                {
                    "type": "intimacao.recebida",
                    "config": {
                        "sources": ["esaj_webhook", "email_parser"],
                        "payload_schema": {"intimacao_id": "int"},
                    },
                }
            ],
        }

    @staticmethod
    def laudo_pronto() -> Dict[str, Any]:
        """Laudo → rascunho no Qwen → protocolo no eSAJ (A3/Windows).

        `protocolo_laudo` NÃO declara `arquivo_path` nos inputs de propósito:
        quando `gerar_laudo` conclui, `routes/jobs.py::_aplicar_resultado`
        exporta o DOCX assinado e injeta o `arquivo_path` no job dependente.
        """
        return {
            "id": "tmpl_laudo_pronto",
            "nome": "Laudo → Geração (Qwen) → Protocolo eSAJ",
            "descricao": (
                "Gera o rascunho do laudo no Qwen local, materializa o DOCX "
                "assinado e protocola no eSAJ pelo agente A3."
            ),
            "versao": 1,
            "tipo": WorkflowType.LAUDO_PRONTO.value,
            "sla_minutos": 30,
            "nodes": [
                {
                    "id": "trigger_laudo",
                    "type": "input",
                    "config": {"event": "laudo.concluido"},
                    "inputs": {},
                    "outputs": [],
                },
                {
                    "id": "gera_laudo",
                    "type": "job_task",
                    "config": {"job_type": "gerar_laudo"},
                    "inputs": {"laudo_id": "ref:trigger"},
                    "outputs": ["markdown"],
                },
                {
                    "id": "protocola_laudo",
                    "type": "job_task",
                    "config": {
                        "job_type": "protocolo_laudo",
                        # arquivo_path é injetado por _aplicar_resultado(gerar_laudo)
                        "arquivo_path_injetado_pela_fila": True,
                    },
                    "inputs": {"laudo_id": "ref:trigger"},
                    "outputs": ["protocolo_numero"],
                },
                {
                    "id": "fim",
                    "type": "output",
                    "config": {"status": "completed"},
                    "inputs": {},
                    "outputs": [],
                },
            ],
            "edges": [
                {"source": "trigger_laudo", "target": "gera_laudo"},
                {"source": "gera_laudo", "target": "protocola_laudo"},
                {"source": "protocola_laudo", "target": "fim"},
            ],
            "triggers": [
                {
                    "type": "laudo.concluido",
                    "config": {"payload_schema": {"laudo_id": "int"}},
                }
            ],
        }

    @staticmethod
    def pagamento_vencido() -> Dict[str, Any]:
        """Pagamento vencido → gera o documento de cobrança.

        Só o `gerar_documento` é real. Envio de e-mail/WhatsApp não tem job
        type, então não virou nó (era o que quebrava o /execute antes).
        """
        return {
            "id": "tmpl_pagamento_vencido",
            "nome": "Pagamento Vencido → Documento de Cobrança",
            "descricao": (
                "Vencimento detectado: gera o documento de cobrança a partir do "
                "template, pronto para envio."
            ),
            "versao": 1,
            "tipo": WorkflowType.PAGAMENTO_VENCIDO.value,
            "sla_minutos": 60,
            "nodes": [
                {
                    "id": "trigger_vencimento",
                    "type": "input",
                    "config": {"event": "pagamento.vencido"},
                    "inputs": {},
                    "outputs": [],
                },
                {
                    "id": "gera_cobranca",
                    "type": "job_task",
                    "config": {"job_type": "gerar_documento"},
                    "inputs": {
                        "template": "cobranca",
                        "dados": "ref:trigger.dados",
                    },
                    "outputs": ["arquivo_path"],
                },
                {
                    "id": "fim",
                    "type": "output",
                    "config": {"status": "completed"},
                    "inputs": {},
                    "outputs": [],
                },
            ],
            "edges": [
                {"source": "trigger_vencimento", "target": "gera_cobranca"},
                {"source": "gera_cobranca", "target": "fim"},
            ],
            "triggers": [
                {
                    "type": "pagamento.vencido",
                    "config": {
                        "cron": "0 0 * * *",
                        "payload_schema": {"lancamento_id": "int", "dados": "object"},
                    },
                }
            ],
        }

    @staticmethod
    def vencimento_critico() -> Dict[str, Any]:
        """Processo parado há >30d → reconfere os autos no eSAJ antes de escalar.

        Escalação/Kanban/notificação não têm job type — a reconferência dos
        autos é o passo automatizável real, e é o que dá base pra escalar.
        """
        return {
            "id": "tmpl_vencimento_critico",
            "nome": "Vencimento Crítico (>30d) → Reconferir Autos",
            "descricao": (
                "Processo vencido há mais de 30 dias: rebaixa os autos do eSAJ "
                "para conferir se houve movimentação antes de escalar."
            ),
            "versao": 1,
            "tipo": WorkflowType.VENCIMENTO_CRITICO.value,
            "sla_minutos": 30,
            "nodes": [
                {
                    "id": "trigger_vencido",
                    "type": "input",
                    "config": {"event": "vencimento.critico"},
                    "inputs": {},
                    "outputs": [],
                },
                {
                    "id": "reconfere_autos",
                    "type": "job_task",
                    "config": {"job_type": "esaj_sincronizar"},
                    "inputs": {"numero_cnj": "ref:trigger.numero_cnj"},
                    "outputs": ["pdf_path"],
                },
                {
                    "id": "fim",
                    "type": "output",
                    "config": {"status": "completed"},
                    "inputs": {},
                    "outputs": [],
                },
            ],
            "edges": [
                {"source": "trigger_vencido", "target": "reconfere_autos"},
                {"source": "reconfere_autos", "target": "fim"},
            ],
            "triggers": [
                {
                    "type": "vencimento.critico",
                    "config": {
                        "cron": "0 8 * * 1-5",
                        "payload_schema": {"processo_id": "int", "numero_cnj": "string"},
                    },
                }
            ],
        }

    @staticmethod
    def erro_laudo() -> Dict[str, Any]:
        """Laudo reprovado na revisão → regera o rascunho no Qwen.

        A notificação do revisor e o "pausar protocolo" não têm job type; o que
        a fila faz de verdade é regerar o rascunho (nova LaudoVersao).
        """
        return {
            "id": "tmpl_erro_laudo",
            "nome": "Erro em Laudo → Regerar Rascunho",
            "descricao": (
                "Laudo reprovado: dispara nova geração do rascunho no Qwen local "
                "criando uma nova versão para revisão."
            ),
            "versao": 1,
            "tipo": WorkflowType.ERRO_LAUDO.value,
            "sla_minutos": 5,
            "nodes": [
                {
                    "id": "trigger_erro",
                    "type": "input",
                    "config": {"event": "laudo.erro"},
                    "inputs": {},
                    "outputs": [],
                },
                {
                    "id": "regera_laudo",
                    "type": "job_task",
                    "config": {"job_type": "gerar_laudo"},
                    "inputs": {"laudo_id": "ref:trigger"},
                    "outputs": ["markdown"],
                },
                {
                    "id": "fim",
                    "type": "output",
                    "config": {"status": "completed"},
                    "inputs": {},
                    "outputs": [],
                },
            ],
            "edges": [
                {"source": "trigger_erro", "target": "regera_laudo"},
                {"source": "regera_laudo", "target": "fim"},
            ],
            "triggers": [
                {
                    "type": "laudo.erro",
                    "config": {
                        "payload_schema": {
                            "laudo_id": "int",
                            "tipo_erro": "string",
                        }
                    },
                }
            ],
        }

    @classmethod
    def get_all_templates(cls) -> Dict[str, Dict[str, Any]]:
        """Retorna todos os 6 templates."""
        return {
            WorkflowType.PROCESSO_CRIADO.value: cls.processo_criado(),
            WorkflowType.INTIMACAO_RECEBIDA.value: cls.intimacao_recebida(),
            WorkflowType.LAUDO_PRONTO.value: cls.laudo_pronto(),
            WorkflowType.PAGAMENTO_VENCIDO.value: cls.pagamento_vencido(),
            WorkflowType.VENCIMENTO_CRITICO.value: cls.vencimento_critico(),
            WorkflowType.ERRO_LAUDO.value: cls.erro_laudo(),
        }

    @classmethod
    def get_template_by_type(cls, workflow_type: str) -> Optional[Dict[str, Any]]:
        """Retorna template por tipo."""
        templates = cls.get_all_templates()
        return templates.get(workflow_type)


class WorkflowBuilder:
    """Builder para customizar templates."""

    def __init__(self, template: Dict[str, Any]):
        self.workflow = json.loads(json.dumps(template))  # Deep copy

    def add_node(self, node: WorkflowNode) -> "WorkflowBuilder":
        """Adiciona nó ao workflow."""
        self.workflow["nodes"].append(asdict(node))
        return self

    def add_edge(self, source: str, target: str) -> "WorkflowBuilder":
        """Adiciona edge ao workflow."""
        self.workflow["edges"].append({"source": source, "target": target})
        return self

    def set_sla(self, minutes: int) -> "WorkflowBuilder":
        """Define SLA em minutos."""
        self.workflow["sla_minutos"] = minutes
        return self

    def set_retry_policy(self, node_id: str, **policy_kwargs) -> "WorkflowBuilder":
        """Define retry policy para nó específico."""
        for node in self.workflow["nodes"]:
            if node["id"] == node_id:
                node["retry_policy"] = policy_kwargs
                break
        return self

    def build(self) -> Dict[str, Any]:
        """Retorna workflow construído."""
        return self.workflow
