# v6/backend/app/modules/ferramentas/{tool}/router.py
from fastapi import APIRouter

router = APIRouter()

"""Cerebro (IA Coordination) — Complete router combining cerebro.py + cerebro_advanced.py.

Endpoints:
- GET /api/v1/cerebro/graph — Mapa fluxo de dados (módulos + kernel + estatísticas)
- POST /api/v1/cerebro/learn — Registrar aprendizado (evento)
- GET /api/v1/cerebro/recommend/{context} — Recomendação inteligente
- GET /api/v1/cerebro/knowledge/{domain} — RAG por departamento
- POST /api/v1/cerebro/workflows/deploy — Deploy workflow template
- GET /api/v1/cerebro/workflows/{workflow_id}/executions — Histórico execuções
- POST /api/v1/cerebro/workflows/{workflow_id}/trigger — Trigger manual
- GET /api/v1/cerebro/monitoring/sla — Dashboard SLA
- GET /api/v1/cerebro/monitoring/escalacoes — Escalações pendentes
- POST /api/v1/cerebro/escalacoes/{id}/resolver — Resolver escalação
- POST /api/v1/cerebro/batch/{workflow_id}/executar — Batch execution
"""
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.middleware import get_current_user
from app.services import get_db
from app.models import User
from app.decorators.require_feature import require_feature_flag

from .schemas import (
    WorkflowDeployRequest,
    WorkflowExecutionResponse,
    TriggerCustomizado,
    BatchJobRequest,
    SLAStatus,
    AprendizadoEventoRequest,
    RecomendacaoResponse,
    ConhecimentoBaseResponse,
)
from .service import (
    WorkflowTemplates,
    WorkflowBuilder,
    classify_event_pattern,
    executar_workflow_async,
    executar_batch_async,
    EscalationEngine,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["cerebro"])


# ============================================================================
# Core Intelligence Endpoints (from cerebro.py)
# ============================================================================

def _contar(db: Session, modulo: str, classe: str) -> int:
    """Conta linhas de uma tabela sem deixar o /graph cair se o model sumir.

    Import tardio de propósito: o Cérebro é módulo isolado e não deve ganhar
    dependência de import em tempo de carga sobre processo/intimação/laudo.
    """
    try:
        import importlib
        model = getattr(importlib.import_module(modulo), classe)
        return db.query(model).count()
    except Exception as e:  # tabela ausente / model movido → 0, nunca 500
        logger.warning(f"[cerebro] contagem {classe} indisponível: {type(e).__name__}: {e}")
        return 0


def _client_host(request: Optional[Request]) -> Optional[str]:
    """IP do chamador. request.client é None em TestClient/ASGI interno."""
    if request is None or request.client is None:
        return None
    return request.client.host


@router.get("/cerebro/graph")
async def get_knowledge_graph(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retorna mapa de fluxo de dados (6 módulos + kernel central + estatísticas).

    Exemplo:
    {
      "modules": [
        {id: "marketing", label: "Marketing", eventos_24h: 45, padrões: 12},
        ...
      ],
      "kernel": {
        "padrões_ativos": 23,
        "confiança_média": 0.84,
        "eventos_24h": 156,
        "taxa_aceição": 0.78
      },
      "flows": [...],
      "stats": {...}
    }
    """
    try:
        from app.models.cerebro import AprendizadoEvento, PadrãoRAG, AuditoriaCAP

        # Query eventos últimas 24h do usuário
        eventos_24h = db.query(AprendizadoEvento).filter(
            AprendizadoEvento.usuario_id == user.id,
            AprendizadoEvento.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).all()

        # Agrupar por origem (módulo)
        modules = {}
        for ev in eventos_24h:
            origem = ev.origem or "operacional"
            if origem not in modules:
                modules[origem] = {"eventos": 0, "padrões": set()}
            modules[origem]["eventos"] += 1
            if ev.padrão_id:
                modules[origem]["padrões"].add(ev.padrão_id)

        # Converter para formato API
        modules_list = [
            {
                "id": k,
                "label": k.title(),
                "eventos_24h": v["eventos"],
                "padrões": len(v["padrões"])
            }
            for k, v in modules.items()
        ]

        # Kernel stats
        padrões_ativos = db.query(PadrãoRAG).filter(
            PadrãoRAG.usuario_id == user.id,
            PadrãoRAG.score >= 0.7
        ).all()

        taxa_aceição = 0.0
        if padrões_ativos:
            total_aceitos = sum(p.aceitos for p in padrões_ativos)
            total_freq = sum(p.frequency for p in padrões_ativos)
            taxa_aceição = total_aceitos / total_freq if total_freq > 0 else 0.0

        confiança_média = sum(p.score for p in padrões_ativos) / len(padrões_ativos) if padrões_ativos else 0.5

        kernel = {
            "padrões_ativos": len(padrões_ativos),
            "confiança_média": round(confiança_média, 2),
            "eventos_24h": len(eventos_24h),
            "taxa_aceição": round(taxa_aceição, 2),
            "padrões_total": db.query(PadrãoRAG).filter(PadrãoRAG.usuario_id == user.id).count()
        }

        # Flows
        flows = []
        for modulo in modules_list:
            flows.append({
                "from": modulo["id"],
                "to": "kernel",
                "type": "ingress",
                "eventos": modulo["eventos_24h"]
            })
            flows.append({
                "from": "kernel",
                "to": modulo["id"],
                "type": "egress",
                "recomendações": modulo["padrões"]
            })

        # Stats — contagem REAL do banco.
        # Antes: 828/835/9725 hardcoded (dado fake em produção, proibido).
        stats = {
            "processes": _contar(db, "app.models.processo", "Processo"),
            "intimacoes": _contar(db, "app.models.kanban", "Intimacao"),
            "laudos": _contar(db, "app.models.laudo", "Laudo"),
            "patterns": kernel["padrões_total"],
            "connections": len(padrões_ativos) * 5,
            "confidence": int(confiança_média * 100)
        }

        # Audit
        audit = AuditoriaCAP(
            usuario_id=user.id,
            endpoint="/cerebro/graph",
            operacao="GET",
            recursos_acessados={"módulos": len(modules_list), "padrões": kernel["padrões_total"]},
            resultado="sucesso"
        )
        db.add(audit)
        db.commit()

        return {
            "modules": modules_list,
            "kernel": kernel,
            "flows": flows,
            "stats": stats
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching graph: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching graph: {str(e)}")


@router.get("/cerebro/learn")
async def list_learning(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Últimos eventos de aprendizado do usuário (mais recentes primeiro).

    O CerebroPage.jsx chama GET /cerebro/learn?limit=10. Só existia o POST,
    então a página recebia 405 e renderizava vazia.
    """
    from app.models.cerebro import AprendizadoEvento

    eventos = (
        db.query(AprendizadoEvento)
        .filter(AprendizadoEvento.usuario_id == user.id)
        .order_by(desc(AprendizadoEvento.timestamp), desc(AprendizadoEvento.id))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": e.id,
            "tipo": e.tipo,
            "origem": e.origem,
            "contexto": e.contexto or {},
            "padrão_id": e.padrão_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in eventos
    ]


@router.post("/cerebro/learn")
async def register_learning(
    payload: AprendizadoEventoRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Registra novo aprendizado (evento)."""
    try:
        from app.models.cerebro import AprendizadoEvento, AuditoriaCAP

        tipo = payload.tipo
        contexto = payload.contexto or {}
        origem = payload.origem
        padrão_id = payload.padrão_id
        idempotency_key = payload.idempotency_key

        # Check duplicata (idempotência)
        if idempotency_key:
            existing = db.query(AprendizadoEvento).filter(
                AprendizadoEvento.usuario_id == user.id,
                AprendizadoEvento.contexto["idempotency_key"].astext == idempotency_key
            ).first()
            if existing:
                return {"status": "duplicata", "evento_id": existing.id}

        # Create event
        evento = AprendizadoEvento(
            usuario_id=user.id,
            tipo=tipo,
            contexto={**contexto, "idempotency_key": idempotency_key} if idempotency_key else contexto,
            origem=origem,
            padrão_id=padrão_id,
            timestamp=datetime.utcnow()
        )
        db.add(evento)
        db.flush()

        # Try to classify with Qwen (fallback to simple classification)
        padrão_id = await classify_event_pattern(tipo, origem, db, user.id)
        if padrão_id:
            evento.padrão_id = padrão_id

        db.commit()
        db.refresh(evento)

        # Audit
        audit = AuditoriaCAP(
            usuario_id=user.id,
            endpoint="/cerebro/learn",
            operacao="POST",
            recursos_acessados={"tipo": tipo, "origem": origem},
            resultado="sucesso",
            ip_address=request.client.host if request else None
        )
        db.add(audit)
        db.commit()

        return {
            "status": "sucesso",
            "evento_id": evento.id,
            "padrão_id": padrão_id,
            "timestamp": evento.timestamp.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error registering event: {str(e)}")


async def _recomendar(
    context: str,
    db: Session,
    user: User,
    request: Optional[Request],
) -> dict:
    """Lógica de recomendação, compartilhada pelas duas rotas (query e path)."""
    try:
        from app.models.cerebro import PadrãoRAG, AprendizadoEvento, AuditoriaCAP

        # Fetch high-confidence patterns para este dominio
        padrões = db.query(PadrãoRAG).filter(
            PadrãoRAG.usuario_id == user.id,
            PadrãoRAG.dominio == context,
            PadrãoRAG.score >= 0.7
        ).order_by(PadrãoRAG.score.desc()).limit(5).all()

        if not padrões:
            recommendation = f"Nenhum padrão aprendido para {context} ainda. Continue usando o sistema para aprender padrões."
            confidence = 0.0
            exemplos = []
        else:
            top_padrão = padrões[0]
            exemplos = db.query(AprendizadoEvento).filter(
                AprendizadoEvento.padrão_id == top_padrão.id
            ).limit(5).all()

            recommendation = top_padrão.descricao
            confidence = top_padrão.score

        # Audit
        audit = AuditoriaCAP(
            usuario_id=user.id,
            endpoint=f"/cerebro/recommend/{context}",
            operacao="GET",
            recursos_acessados={"context": context, "padrões_retornados": len(padrões)},
            resultado="sucesso",
            ip_address=_client_host(request)
        )
        db.add(audit)
        db.commit()

        return {
            "context": context,
            "recommendation": recommendation,
            "confidence": round(confidence, 2),
            "exemplos": [e.id for e in exemplos],
            "padrões_alternativos": [p.descricao for p in padrões[1:]]
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error getting recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recommendation: {str(e)}")


@router.get("/cerebro/recommend", response_model=RecomendacaoResponse)
async def get_recommendation_query(
    context: str = Query(..., description="marketing, vendas, engenharia, financeiro, operacional"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Recomendação por query param — formato que o CerebroPage.jsx usa (dava 404)."""
    return await _recomendar(context, db, user, request)


@router.get("/cerebro/recommend/{context}", response_model=RecomendacaoResponse)
async def get_recommendation(
    context: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Recomendação por path param — mantida para compatibilidade."""
    return await _recomendar(context, db, user, request)


@router.get("/cerebro/knowledge/{domain}", response_model=ConhecimentoBaseResponse)
async def get_domain_knowledge(
    domain: str,
    query: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Retorna base de conhecimento RAG por departamento."""
    try:
        from app.models.cerebro import PadrãoRAG, AuditoriaCAP

        # Query padrões deste dominio
        query_obj = db.query(PadrãoRAG).filter(
            PadrãoRAG.usuario_id == user.id,
            PadrãoRAG.dominio == domain
        )

        if query:
            query_obj = query_obj.filter(PadrãoRAG.descricao.ilike(f"%{query}%"))

        padrões = query_obj.order_by(PadrãoRAG.score.desc()).limit(20).all()

        knowledge_base = [
            {
                "id": p.id,
                "tipo": p.tipo,
                "descricao": p.descricao,
                "score": p.score,
                "frequency": p.frequency,
                "aceitos": p.aceitos,
                "metadata": p.metadata
            }
            for p in padrões
        ]

        # Audit
        audit = AuditoriaCAP(
            usuario_id=user.id,
            endpoint=f"/cerebro/knowledge/{domain}",
            operacao="GET",
            recursos_acessados={"domain": domain, "query": query, "resultados": len(padrões)},
            resultado="sucesso",
            ip_address=request.client.host if request else None
        )
        db.add(audit)
        db.commit()

        return {
            "domain": domain,
            "query": query,
            "resultados": len(padrões),
            "knowledge_base": knowledge_base
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching knowledge: {str(e)}")


# ============================================================================
# Workflow Management Endpoints (from cerebro_advanced.py)
# ============================================================================

@router.post("/cerebro/workflows/deploy")
async def deploy_workflow(
    request: WorkflowDeployRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Deploy workflow template (ou customizado)."""
    try:
        from app.models import WorkflowDefinition

        logger.info(f"Deploy workflow: {request.tipo}")

        # 1. Busca template
        template = WorkflowTemplates.get_template_by_type(request.tipo)
        if not template:
            raise HTTPException(status_code=400, detail=f"Template não encontrado: {request.tipo}")

        # 2. Customiza se necessário
        if request.nome_customizado:
            template["nome"] = request.nome_customizado
        if request.sla_minutos:
            template["sla_minutos"] = request.sla_minutos

        # 3. Persiste no DB
        workflow_def = WorkflowDefinition(
            nome=template["nome"],
            descricao=template.get("descricao"),
            versao=template["versao"],
            nodes=template["nodes"],
            edges=template["edges"],
            triggers=template["triggers"],
            ativa=request.ativa,
            criado_por=user.id
        )

        db.add(workflow_def)
        db.commit()

        logger.info(f"Workflow deployed: {workflow_def.id}")

        return {
            "id": workflow_def.id,
            "nome": workflow_def.nome,
            "versao": workflow_def.versao,
            "status": "deployed",
            "url_monitor": f"/api/v1/cerebro/workflows/{workflow_def.id}/executions"
        }

    except Exception as e:
        logger.error(f"Erro deploy workflow: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cerebro/workflows/{workflow_id}/executions")
async def get_workflow_executions(
    workflow_id: int,
    limit: int = Query(50, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Retorna histórico de execuções de workflow."""
    try:
        from app.models import WorkflowExecution

        query = db.query(WorkflowExecution).filter_by(definition_id=workflow_id)

        if status:
            query = query.filter_by(status=status)

        total = query.count()
        executions = query.order_by(desc(WorkflowExecution.iniciado_em)).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "executions": [
                {
                    "id": e.id,
                    "status": e.status,
                    "trigger_event": e.trigger_event,
                    "iniciado_em": e.iniciado_em.isoformat(),
                    "concluido_em": e.concluido_em.isoformat() if e.concluido_em else None,
                    "tempo_total_min": (
                        (e.concluido_em - e.iniciado_em).total_seconds() / 60
                        if e.concluido_em else None
                    ),
                    "sucesso": e.status == "completed"
                }
                for e in executions
            ]
        }

    except Exception as e:
        logger.error(f"Erro buscando execuções: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cerebro/workflows/{workflow_id}/trigger")
async def trigger_workflow_manual(
    workflow_id: int,
    trigger_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Dispara workflow manualmente (para testes ou override)."""
    try:
        from app.models import WorkflowDefinition, WorkflowExecution

        logger.info(f"Manual trigger workflow: {workflow_id}")

        # 1. Busca workflow definition
        defn = db.query(WorkflowDefinition).filter_by(id=workflow_id).first()
        if not defn:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")

        # 2. Cria execução
        execution = WorkflowExecution(
            definition_id=workflow_id,
            trigger_event="manual",
            trigger_id=trigger_data.get("processo_id"),
            status="queued",
            node_results={}
        )

        db.add(execution)
        db.commit()

        logger.info(f"Workflow execution criada: {execution.id}")

        # 3. Enfileira para execução (async em background)
        if background_tasks:
            background_tasks.add_task(
                executar_workflow_async,
                execution_id=execution.id,
                db_url=os.getenv("DATABASE_URL")
            )

        return {
            "execution_id": execution.id,
            "status": "queued",
            "url_monitor": f"/api/v1/cerebro/workflows/{workflow_id}/executions"
        }

    except Exception as e:
        logger.error(f"Erro triggerando workflow: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cerebro/monitoring/sla")
async def get_sla_dashboard(
    dias: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Dashboard de SLA (ultimas N dias)."""
    try:
        from app.models import WorkflowDefinition, WorkflowExecution

        data_inicio = datetime.utcnow() - timedelta(days=dias)
        workflows = db.query(WorkflowDefinition).filter_by(ativa=True).all()

        workflows_stats = []
        total_execucoes = 0
        total_dentro_sla = 0

        for wf in workflows:
            execucoes = db.query(WorkflowExecution).filter(
                WorkflowExecution.definition_id == wf.id,
                WorkflowExecution.iniciado_em >= data_inicio
            ).all()

            dentro_sla = 0
            tempo_total = 0

            for exec in execucoes:
                if exec.concluido_em:
                    tempo = (exec.concluido_em - exec.iniciado_em).total_seconds() / 60
                    tempo_total += tempo

                    sla_minutos = wf.criado_em.get("sla_minutos", 120) if isinstance(wf.criado_em, dict) else 120
                    if tempo <= sla_minutos:
                        dentro_sla += 1

            percentual = (dentro_sla / len(execucoes) * 100) if execucoes else 0
            tempo_medio = tempo_total / len(execucoes) if execucoes else 0

            status = "ok"
            if percentual < 80:
                status = "warning"
            if percentual < 50:
                status = "critical"

            workflows_stats.append({
                "id": wf.id,
                "nome": wf.nome,
                "sla_minutos": wf.criado_em.get("sla_minutos", 120) if isinstance(wf.criado_em, dict) else 120,
                "execucoes_total": len(execucoes),
                "dentro_sla": dentro_sla,
                "percentual_sla": percentual,
                "tempo_medio_min": tempo_medio,
                "status": status
            })

            total_execucoes += len(execucoes)
            total_dentro_sla += dentro_sla

        percentual_geral = (total_dentro_sla / total_execucoes * 100) if total_execucoes else 0
        alertas = sum(1 for w in workflows_stats if w["status"] == "warning")
        criticos = sum(1 for w in workflows_stats if w["status"] == "critical")

        return {
            "periodo_dias": dias,
            "workflows": workflows_stats,
            "resumo": {
                "percentual_geral": percentual_geral,
                "alertas": alertas,
                "criticos": criticos
            }
        }

    except Exception as e:
        logger.error(f"Erro calculando SLA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cerebro/monitoring/escalacoes")
async def get_escalacoes_pendentes(
    horas: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Retorna escalações pendentes das últimas N horas."""
    try:
        from app.models import AuditLog

        data_limite = datetime.utcnow() - timedelta(hours=horas)

        escalacoes = db.query(AuditLog).filter(
            AuditLog.acao.like("escalacao_%"),
            AuditLog.created_at >= data_limite
        ).order_by(desc(AuditLog.created_at)).all()

        escalacoes_list = []
        criticas = 0

        for e in escalacoes:
            detalhes = e.detalhes or {}
            nivel = detalhes.get("nivel", "warning")

            if nivel == "critical":
                criticas += 1

            escalacoes_list.append({
                "id": e.id,
                "motivo": detalhes.get("motivo"),
                "nivel": nivel,
                "timestamp": e.created_at.isoformat(),
                "contexto": detalhes.get("contexto", {}),
                "resolvido": "resolvido_em" in detalhes
            })

        return {
            "total": len(escalacoes_list),
            "criticas": criticas,
            "escalacoes": escalacoes_list
        }

    except Exception as e:
        logger.error(f"Erro buscando escalações: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cerebro/escalacoes/{escalacao_id}/resolver")
async def resolver_escalacao(
    escalacao_id: int,
    notas: str = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Marca escalação como resolvida."""
    try:
        escalation = EscalationEngine(db)
        sucesso = await escalation.resolver_escalacao(
            escalacao_id=escalacao_id,
            resolvido_por=user.username,
            notas=notas
        )

        if not sucesso:
            raise HTTPException(status_code=404, detail="Escalação não encontrada")

        return {"status": "resolvida", "escalacao_id": escalacao_id}

    except Exception as e:
        logger.error(f"Erro resolvendo escalação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cerebro/batch/{workflow_id}/executar")
async def executar_batch_workflow(
    workflow_id: int,
    request: BatchJobRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Executa workflow em paralelo para múltiplos processos (100+)."""
    try:
        from app.models import Processo

        logger.info(f"Batch workflow: {workflow_id}")

        # Filtra processos
        query = db.query(Processo)
        for chave, valor in request.filtro_processos.items():
            if hasattr(Processo, chave):
                query = query.filter(getattr(Processo, chave) == valor)

        processos = query.all()

        if not processos:
            raise HTTPException(status_code=400, detail="Nenhum processo encontrado")

        # Cria batch job
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{workflow_id}"

        # Enfileira batch em background
        if background_tasks:
            background_tasks.add_task(
                executar_batch_async,
                batch_id=batch_id,
                workflow_id=workflow_id,
                processo_ids=[p.id for p in processos],
                paralelizar=request.paralelizar,
                db_url=os.getenv("DATABASE_URL")
            )

        logger.info(f"Batch job criado: {batch_id} com {len(processos)} processos")

        return {
            "batch_id": batch_id,
            "total_processos": len(processos),
            "status": "iniciado",
            "url_monitor": f"/api/v1/cerebro/batch/{batch_id}/status"
        }

    except Exception as e:
        logger.error(f"Erro criando batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))
