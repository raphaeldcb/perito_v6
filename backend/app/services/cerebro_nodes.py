"""Cérebro Phase 2 — 40 Node Types Expandidos.

Tipos de nós para workflow engine:
- Análise de processos
- Geração de documentos
- Notificações
- Integração com APIs externas

Cada nó tem: execute(node_def, inputs, execution, engine) -> output_dict
"""
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
import requests
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Process, Intimacao, Laudo, Job
from app.services.cerebro_engine import CerebroExecutionEngine

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Registro central de node types."""

    def __init__(self):
        self.nodes: Dict[str, Callable] = {}

    def register(self, node_type: str, handler: Callable):
        """Registra um node type."""
        self.nodes[node_type] = handler

    def get(self, node_type: str) -> Optional[Callable]:
        """Obtém handler de um node type."""
        return self.nodes.get(node_type)

    def list_types(self) -> list:
        """Lista todos os node types."""
        return list(self.nodes.keys())


# ============================================================================
# NODE REGISTRY GLOBAL
# ============================================================================
node_registry = NodeRegistry()


# ============================================================================
# GRUPO 1: INPUT/OUTPUT (2 nós)
# ============================================================================

def node_input_trigger(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Nó de entrada: captura dados do trigger."""
    return {
        "trigger_id": execution.trigger_id,
        "trigger_event": execution.trigger_event,
        "trigger_payload": inputs,
    }


def node_output_result(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Nó de saída: formata resultado final."""
    return {
        "success": True,
        "result": inputs,
        "timestamp": datetime.utcnow().isoformat(),
    }


node_registry.register("input_trigger", node_input_trigger)
node_registry.register("output_result", node_output_result)


# ============================================================================
# GRUPO 2: ANÁLISE DE PROCESSOS (8 nós)
# ============================================================================

def node_analyze_process(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Analisa processo: extrai metadados, datas, partes."""
    db = engine.db
    process_id = inputs.get("process_id")

    process = db.query(Process).get(process_id)
    if not process:
        raise ValueError(f"Processo {process_id} não encontrado")

    return {
        "process_id": process.id,
        "numero_processo": getattr(process, "numero_processo", None),
        "data_cadastro": process.created_at.isoformat() if process.created_at else None,
        "status": getattr(process, "status", "unknown"),
        "area": getattr(process, "area", None),
        "comarca": getattr(process, "comarca", None),
        "vara": getattr(process, "vara", None),
    }


def node_check_deadline(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Verifica se processo está com prazo vencido/próximo."""
    db = engine.db
    process_id = inputs.get("process_id")
    days_threshold = inputs.get("days_threshold", 30)

    process = db.query(Process).get(process_id)
    if not process:
        raise ValueError(f"Processo {process_id} não encontrado")

    deadline = getattr(process, "deadline", None)
    if not deadline:
        return {"is_overdue": False, "days_remaining": None}

    today = datetime.utcnow().date()
    deadline_date = deadline if isinstance(deadline, (datetime,)) else deadline
    days_remaining = (deadline_date - today).days

    return {
        "is_overdue": days_remaining < 0,
        "days_remaining": days_remaining,
        "deadline": deadline_date.isoformat() if deadline_date else None,
        "is_critical": 0 < days_remaining <= days_threshold,
    }


def node_extract_legal_area(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Extrai área jurídica do processo (engenharia, civil, tributário, etc)."""
    # TODO: Integrar com Qwen para classificação automática
    numero_processo = inputs.get("numero_processo")

    # Fallback simples (baseado em descrição)
    description = inputs.get("description", "")

    areas = {
        "engenharia": ["perícia", "vistoria", "laudo"],
        "civil": ["cobrança", "contrato", "responsabilidade"],
        "tributário": ["imposto", "ICMS", "IPI"],
        "trabalhista": ["justa causa", "demissão", "CLT"],
        "criminal": ["crime", "roubo", "agressão"],
    }

    detected_area = "civil"  # Default
    for area, keywords in areas.items():
        if any(kw in description.lower() for kw in keywords):
            detected_area = area
            break

    return {"area": detected_area, "confidence": 0.7}


def node_count_attachments(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Conta anexos/documentos do processo."""
    db = engine.db
    process_id = inputs.get("process_id")

    process = db.query(Process).get(process_id)
    if not process:
        return {"count": 0, "types": {}}

    # Simplificado: contar Intimacao (representa documentos)
    intimacoes = db.query(Intimacao).filter(
        Intimacao.process_id == process_id
    ).count()

    return {"count": intimacoes, "types": {"intimacoes": intimacoes}}


def node_check_lawyer_response(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Verifica se advogado respondeu a intimação (status)."""
    db = engine.db
    intimacao_id = inputs.get("intimacao_id")

    intimacao = db.query(Intimacao).get(intimacao_id)
    if not intimacao:
        return {"responded": False, "response_date": None}

    responded = getattr(intimacao, "status", "pending") == "respondida"
    response_date = getattr(intimacao, "response_date", None)

    return {
        "responded": responded,
        "response_date": response_date.isoformat() if response_date else None,
        "status": getattr(intimacao, "status", "pending"),
    }


def node_calculate_costs(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Calcula custos (custas, honorários) do processo."""
    db = engine.db
    process_id = inputs.get("process_id")

    process = db.query(Process).get(process_id)
    if not process:
        return {"custas": 0, "honorarios": 0, "total": 0}

    # Simplificado: estimar baseado em valor da causa
    valor_causa = getattr(process, "valor_causa", 0) or 0
    custas = valor_causa * 0.01  # 1% estimado
    honorarios = valor_causa * 0.05  # 5% estimado

    return {
        "custas": float(custas),
        "honorarios": float(honorarios),
        "total": float(custas + honorarios),
        "valor_causa": float(valor_causa),
    }


def node_assess_risk(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Avalia risco do processo (ganho/perda/incerto)."""
    # Simplificado: baseado em parâmetros
    prognosis = inputs.get("prognosis", "incerto")  # ganho, perda, incerto

    risk_map = {
        "ganho": {"risk_level": "baixo", "success_probability": 0.85},
        "perda": {"risk_level": "alto", "success_probability": 0.15},
        "incerto": {"risk_level": "médio", "success_probability": 0.5},
    }

    return risk_map.get(prognosis, risk_map["incerto"])


node_registry.register("analyze_process", node_analyze_process)
node_registry.register("check_deadline", node_check_deadline)
node_registry.register("extract_legal_area", node_extract_legal_area)
node_registry.register("count_attachments", node_count_attachments)
node_registry.register("check_lawyer_response", node_check_lawyer_response)
node_registry.register("calculate_costs", node_calculate_costs)
node_registry.register("assess_risk", node_assess_risk)


# ============================================================================
# GRUPO 3: GERAÇÃO DE DOCUMENTOS (10 nós)
# ============================================================================

def node_generate_office(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Gera ofício baseado em template."""
    template = inputs.get("template", "default")
    processo_id = inputs.get("processo_id")

    # Simplificado: mock de geração
    oficio_content = f"""OFÍCIO Nº 001/2026

Processo nº {processo_id}

Prezados Senhores,

Segue anexado laudo técnico conforme solicitado.

Atenciosamente,
IPC-MS"""

    return {
        "oficio_id": f"oficio_{processo_id}_{int(datetime.utcnow().timestamp())}",
        "content": oficio_content,
        "template": template,
        "generated_at": datetime.utcnow().isoformat(),
    }


def node_generate_report(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Gera relatório técnico."""
    report_type = inputs.get("report_type", "technical")

    report = f"""RELATÓRIO {report_type.upper()}

Data: {datetime.utcnow().isoformat()}

Resumo: Análise técnica completa do processo.
"""

    return {
        "report_id": f"report_{int(datetime.utcnow().timestamp())}",
        "content": report,
        "type": report_type,
    }


def node_generate_expertise_report(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Gera laudo pericial (expertise)."""
    area = inputs.get("area", "engenharia")
    process_id = inputs.get("process_id")

    # TODO: Integrar com Qwen para geração automática de laudo
    laudo_content = f"""LAUDO PERICIAL

Área: {area}
Processo: {process_id}
Data: {datetime.utcnow().isoformat()}

1. INTRODUÇÃO
Apresentamos o presente laudo técnico de perícia em {area}.

2. METODOLOGIA
Análise técnica conforme padrões da ABNT.

3. CONCLUSÃO
Conforme análise realizada, conclui-se que...

Atenciosamente,
Perito Judicial"""

    return {
        "laudo_id": f"laudo_{process_id}_{int(datetime.utcnow().timestamp())}",
        "content": laudo_content,
        "area": area,
    }


def node_format_document(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Formata documento (PDF, DOCX)."""
    content = inputs.get("content")
    format_type = inputs.get("format", "pdf")

    # Simplificado: mock de formatting
    return {
        "format": format_type,
        "size_bytes": len(str(content)) * 10 if content else 0,
        "formatted": True,
        "hash": "mock_hash",
    }


def node_sign_document(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Assina documento (mock de A3/WebSigner)."""
    doc_id = inputs.get("doc_id")
    # TODO: Integrar com A3/WebSigner real no Windows

    return {
        "signed": True,
        "signature_hash": "mock_signature_hash",
        "signed_at": datetime.utcnow().isoformat(),
        "certificate": "mock_certificate_cn",
    }


def node_upload_to_onedrive(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Faz upload de documento para OneDrive."""
    doc_id = inputs.get("doc_id")
    folder = inputs.get("folder", "LAUDOS")

    # TODO: Integrar com Azure Graph API
    return {
        "uploaded": True,
        "url": f"https://onedrive.com/mock/{folder}/{doc_id}",
        "folder": folder,
    }


def node_archive_document(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Arquiva documento no banco (database blob)."""
    db = engine.db
    doc_id = inputs.get("doc_id")
    content = inputs.get("content")
    process_id = inputs.get("process_id")

    # Simplificado: mock de archiving
    return {
        "archived": True,
        "doc_id": doc_id,
        "process_id": process_id,
        "archived_at": datetime.utcnow().isoformat(),
    }


def node_create_template_instance(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Cria instância de template (ofício, laudo, etc)."""
    template_id = inputs.get("template_id")
    variables = inputs.get("variables", {})

    # Simplificado: mock substitution
    instance = f"Template {template_id} with vars {json.dumps(variables)}"

    return {
        "instance_id": f"instance_{int(datetime.utcnow().timestamp())}",
        "content": instance,
        "template_id": template_id,
    }


def node_validate_document(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Valida estrutura e conteúdo de documento."""
    content = inputs.get("content", "")
    doc_type = inputs.get("doc_type", "oficio")

    # Simplificado: validações básicas
    is_valid = len(content) > 50  # Mínimo de conteúdo

    return {
        "valid": is_valid,
        "doc_type": doc_type,
        "errors": [] if is_valid else ["Documento vazio ou muito pequeno"],
        "warnings": [],
    }


node_registry.register("generate_office", node_generate_office)
node_registry.register("generate_report", node_generate_report)
node_registry.register("generate_expertise_report", node_generate_expertise_report)
node_registry.register("format_document", node_format_document)
node_registry.register("sign_document", node_sign_document)
node_registry.register("upload_to_onedrive", node_upload_to_onedrive)
node_registry.register("archive_document", node_archive_document)
node_registry.register("create_template_instance", node_create_template_instance)
node_registry.register("validate_document", node_validate_document)


# ============================================================================
# GRUPO 4: NOTIFICAÇÕES (6 nós)
# ============================================================================

def node_send_email(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Envia email."""
    to_email = inputs.get("to_email")
    subject = inputs.get("subject")
    body = inputs.get("body")

    # TODO: Integrar com SMTP real
    logger.info(f"Email to {to_email}: {subject}")

    return {
        "sent": True,
        "email_id": f"email_{int(datetime.utcnow().timestamp())}",
        "to": to_email,
        "subject": subject,
    }


def node_send_whatsapp(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Envia WhatsApp."""
    phone = inputs.get("phone")
    message = inputs.get("message")

    # TODO: Integrar com API WhatsApp
    logger.info(f"WhatsApp to {phone}: {message}")

    return {
        "sent": True,
        "whatsapp_id": f"wa_{int(datetime.utcnow().timestamp())}",
        "phone": phone,
    }


def node_send_sms(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Envia SMS."""
    phone = inputs.get("phone")
    message = inputs.get("message")

    # TODO: Integrar com API SMS
    logger.info(f"SMS to {phone}: {message}")

    return {
        "sent": True,
        "sms_id": f"sms_{int(datetime.utcnow().timestamp())}",
        "phone": phone,
    }


def node_post_to_slack(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Posta mensagem em Slack."""
    channel = inputs.get("channel", "#geral")
    message = inputs.get("message")

    # TODO: Integrar com Slack API
    logger.info(f"Slack {channel}: {message}")

    return {
        "posted": True,
        "message_id": f"slack_{int(datetime.utcnow().timestamp())}",
        "channel": channel,
    }


def node_create_notification(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Cria notificação no sistema."""
    user_id = inputs.get("user_id")
    title = inputs.get("title")
    message = inputs.get("message")

    # Simplificado: mock
    return {
        "notification_id": f"notif_{int(datetime.utcnow().timestamp())}",
        "user_id": user_id,
        "title": title,
        "created_at": datetime.utcnow().isoformat(),
    }


def node_log_event(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Registra evento em log/auditoria."""
    event_type = inputs.get("event_type")
    details = inputs.get("details", {})

    logger.info(f"Event: {event_type}, Details: {json.dumps(details)}")

    return {
        "logged": True,
        "event_id": f"event_{int(datetime.utcnow().timestamp())}",
        "type": event_type,
    }


node_registry.register("send_email", node_send_email)
node_registry.register("send_whatsapp", node_send_whatsapp)
node_registry.register("send_sms", node_send_sms)
node_registry.register("post_to_slack", node_post_to_slack)
node_registry.register("create_notification", node_create_notification)
node_registry.register("log_event", node_log_event)


# ============================================================================
# GRUPO 5: INTEGRAÇÃO COM APIS (8 nós)
# ============================================================================

def node_query_datajud(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Consulta DataJud (API CNJ)."""
    numero_processo = inputs.get("numero_processo")

    # TODO: Integrar com DataJud real
    return {
        "found": True,
        "numero_processo": numero_processo,
        "status": "ativo",
        "movimentacoes": [],
    }


def node_query_esaj(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Consulta e-SAJ (TJ)."""
    numero_processo = inputs.get("numero_processo")
    tribunal = inputs.get("tribunal", "TJMS")

    # TODO: Integrar com e-SAJ real
    return {
        "found": True,
        "numero_processo": numero_processo,
        "tribunal": tribunal,
        "autos": [],
    }


def node_query_pje(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Consulta PJe (CNJ Justiça Federal/Trabalho)."""
    numero_processo = inputs.get("numero_processo")

    # TODO: Integrar com PJe real
    return {
        "found": True,
        "numero_processo": numero_processo,
        "instance": "primeira",
    }


def node_download_from_url(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Baixa arquivo de URL."""
    url = inputs.get("url")

    # Simplificado: mock download
    return {
        "downloaded": True,
        "url": url,
        "size_bytes": 1024,
        "filename": url.split("/")[-1],
    }


def node_call_webhook(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Chama webhook externo."""
    webhook_url = inputs.get("webhook_url")
    payload = inputs.get("payload", {})

    # TODO: Fazer request real
    logger.info(f"Webhook call to {webhook_url}")

    return {
        "called": True,
        "webhook_url": webhook_url,
        "response_code": 200,
    }


def node_query_rag(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Consulta RAG (base de conhecimento)."""
    query = inputs.get("query")
    domain = inputs.get("domain", "geral")

    # TODO: Integrar com RAG real (pgvector)
    return {
        "results": [],
        "query": query,
        "domain": domain,
        "count": 0,
    }


def node_call_qwen(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Chama Qwen (IA local)."""
    prompt = inputs.get("prompt")

    # TODO: Integrar com Ollama/Qwen
    logger.info(f"Qwen call: {prompt[:50]}...")

    return {
        "result": "Mock Qwen response",
        "prompt": prompt,
        "tokens_used": 150,
    }


def node_call_deepseek(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Chama DeepSeek (supervisão)."""
    query = inputs.get("query")

    # TODO: Integrar com DeepSeek API
    logger.info(f"DeepSeek call: {query[:50]}...")

    return {
        "result": "Mock DeepSeek response",
        "query": query,
    }


node_registry.register("query_datajud", node_query_datajud)
node_registry.register("query_esaj", node_query_esaj)
node_registry.register("query_pje", node_query_pje)
node_registry.register("download_from_url", node_download_from_url)
node_registry.register("call_webhook", node_call_webhook)
node_registry.register("query_rag", node_query_rag)
node_registry.register("call_qwen", node_call_qwen)
node_registry.register("call_deepseek", node_call_deepseek)


# ============================================================================
# GRUPO 6: CONTROLE DE FLUXO (4 nós)
# ============================================================================

def node_decision(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Decisão condicional (if/else)."""
    condition = inputs.get("condition", False)
    true_branch = inputs.get("true_branch")
    false_branch = inputs.get("false_branch")

    branch = true_branch if condition else false_branch

    return {
        "condition": condition,
        "selected_branch": branch,
        "timestamp": datetime.utcnow().isoformat(),
    }


def node_loop(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Loop sobre lista de itens."""
    items = inputs.get("items", [])
    iterations = 0

    for item in items:
        # Simplificado: mock de processamento
        iterations += 1

    return {
        "iterations": iterations,
        "items_count": len(items),
    }


def node_delay(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Aguarda tempo especificado."""
    delay_seconds = inputs.get("delay_seconds", 60)

    # Não implementar sleep real (seria bloqueante)
    # Apenas registrar que deveria aguardar
    return {
        "delay_seconds": delay_seconds,
        "scheduled_resume": (
            datetime.utcnow() + timedelta(seconds=delay_seconds)
        ).isoformat(),
    }


def node_parallel_join(
    node_def: Dict[str, Any],
    inputs: Dict[str, Any],
    execution: Any,
    engine: CerebroExecutionEngine,
) -> Dict[str, Any]:
    """Aguarda conclusão de múltiplos nós paralelos."""
    results = inputs.get("results", [])

    return {
        "joined": True,
        "results_count": len(results),
        "timestamp": datetime.utcnow().isoformat(),
    }


node_registry.register("decision", node_decision)
node_registry.register("loop", node_loop)
node_registry.register("delay", node_delay)
node_registry.register("parallel_join", node_parallel_join)
