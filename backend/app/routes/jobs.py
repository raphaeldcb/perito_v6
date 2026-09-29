"""Fila de jobs: o mac_agent puxa trabalho e reporta resultado real.

Autenticação do agente: header X-Agent-Key == settings.agent_api_key.
Consulta de status por usuários: JWT normal.

FIX #6: Deadman timer — jobs órfãos são reapados após 5min de inatividade.
"""
from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.middleware import get_current_user
from app.models import Job, Intimacao, Processo, KanbanCartao, User
from app.services import get_db
from app.services import workflow_engine

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT = 300  # 5 min — job sem heartbeat é considerado órfão


def verificar_agente(x_agent_key: str = Header(None)):
    if not settings.agent_api_key:
        raise HTTPException(status_code=503, detail="AGENT_API_KEY não configurada no servidor")
    if x_agent_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Chave de agente inválida")


def reap_stale_jobs(db: Session):
    """FIX #6: Reaper — marca jobs órfãos como erro para voltar à fila.

    Job é órfão se esteve "processando" por > HEARTBEAT_TIMEOUT sem heartbeat.
    """
    cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT)
    stale = db.query(Job).filter(
        Job.status == "processando",
        (Job.last_heartbeat.isnot(None) & (Job.last_heartbeat < cutoff)) |
        ((Job.last_heartbeat.is_(None)) & (Job.iniciado_em < cutoff))
    ).all()

    reaped = 0
    for job in stale:
        logger.warning(f"🪦 Reaping stale job {job.id} (type={job.tipo}, executor={job.executor})")
        job.status = "na_fila"
        job.executor = None
        job.last_heartbeat = None
        reaped += 1
    if reaped:
        db.commit()
        logger.info(f"Reaped {reaped} stale job(s)")
    return reaped


class JobConcluir(BaseModel):
    sucesso: bool
    resultado: dict | None = None
    erro: str | None = None


@router.get("")
async def listar_jobs(
    status_filtro: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Job)
    if status_filtro:
        query = query.filter(Job.status == status_filtro)
    return query.order_by(Job.id.desc()).limit(limit).all()


@router.get("/metrics")
async def get_metrics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """GET /api/v1/jobs/metrics

    Retorna métricas de jobs para dashboard:
    - queued: lista de jobs na fila
    - processing: lista de jobs em processamento
    - completed_today: contagem de jobs completados hoje
    - avg_time_seconds: tempo médio de processamento (em segundos)

    Resposta:
    {
        "queued": [{"id": 1, "tipo": "esaj_download", "criado_em": "2026-08-19T10:00:00"}],
        "processing": [{"id": 2, "tipo": "protocolo", "iniciado_em": "2026-08-19T10:30:00"}],
        "completed_today": 5,
        "avg_time_seconds": 120.5
    }
    """
    # Jobs na fila
    queued_jobs = db.query(Job).filter(Job.status == "na_fila").order_by(Job.id).all()
    queued = [
        {
            "id": job.id,
            "tipo": job.tipo,
            "criado_em": job.created_at.isoformat() if job.created_at else None,
        }
        for job in queued_jobs
    ]

    # Jobs em processamento
    processing_jobs = db.query(Job).filter(Job.status == "processando").all()
    processing = [
        {
            "id": job.id,
            "tipo": job.tipo,
            "executor": job.executor,
            "iniciado_em": job.iniciado_em.isoformat() if job.iniciado_em else None,
        }
        for job in processing_jobs
    ]

    # Jobs completados hoje (UTC)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = db.query(Job).filter(
        Job.status == "concluido",
        Job.concluido_em >= today_start,
    ).count()

    # Tempo médio de processamento (para jobs completados)
    completed_jobs = db.query(Job).filter(
        Job.status == "concluido",
        Job.iniciado_em.isnot(None),
        Job.concluido_em.isnot(None),
    ).all()

    avg_time_seconds = 0.0
    if completed_jobs:
        total_seconds = 0.0
        for job in completed_jobs:
            delta = job.concluido_em - job.iniciado_em
            total_seconds += delta.total_seconds()
        avg_time_seconds = round(total_seconds / len(completed_jobs), 2)

    # Convert to frontend format (WorkflowMetricsData)
    active_jobs = []
    for job in queued_jobs:
        active_jobs.append({
            "job_id": str(job.id),
            "type": job.tipo,
            "status": "queued",
            "created_at": job.created_at.isoformat() if job.created_at else None,
        })
    for job in processing_jobs:
        active_jobs.append({
            "job_id": str(job.id),
            "type": job.tipo,
            "status": "processing",
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.iniciado_em.isoformat() if job.iniciado_em else None,
        })

    return {
        "pipeline": {
            "queued": len(queued),
            "processing": len(processing),
            "done": completed_today,
        },
        "active_jobs": active_jobs,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/proximo")
async def proximo_job(
    tipo: str = None,
    executor: str = "mac-agent",
    db: Session = Depends(get_db),
    _=Depends(verificar_agente),
):
    """Claim atômico do próximo job da fila (para o agente Mac).

    FIX #6: Antes de atribuir, reapa jobs órfãos que ficaram presos.
    """
    # Reap stale jobs first
    reap_stale_jobs(db)

    query = db.query(Job).filter(Job.status == "na_fila")
    if tipo:
        query = query.filter(Job.tipo == tipo)

    candidatos = query.order_by(Job.id).with_for_update(skip_locked=True).limit(20).all()
    job = None
    for candidato in candidatos:
        dep_id = (candidato.payload or {}).get("aguardar_job_id")
        if dep_id:
            dep = db.query(Job).filter(Job.id == dep_id).first()
            if not dep or dep.status != "concluido":
                continue  # dependência ainda não pronta — segura na fila
        job = candidato
        break
    if not job:
        db.rollback()
        return {"job": None}

    job.status = "processando"
    job.executor = executor
    job.iniciado_em = datetime.utcnow()
    job.last_heartbeat = datetime.utcnow()  # Inicia heartbeat quando job é reivindicado
    job.tentativas += 1
    db.commit()
    db.refresh(job)
    return {
        "job": {
            "id": job.id,
            "tipo": job.tipo,
            "payload": job.payload,
            "tentativas": job.tentativas,
        }
    }


@router.patch("/{job_id}/concluir")
async def concluir_job(
    job_id: int,
    payload: JobConcluir,
    db: Session = Depends(get_db),
    _=Depends(verificar_agente),
):
    # FIX #10: Row-level lock (SELECT FOR UPDATE) evita race condition entre múltiplos agents
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    # FIX #10: Idempotência check — se job já foi concluído, retorna o status anterior
    # (múltiplos agents tentando reportar o mesmo job → first writer wins)
    if job.status in ("concluido", "erro"):
        # Job já foi concluído por outro agent — retorna 409 para o agent retentar
        raise HTTPException(
            status_code=409,
            detail=f"Job já foi finalizado com status '{job.status}'. Último resultado: {job.resultado}"
        )

    if payload.sucesso:
        job.status = "concluido"
        job.resultado = payload.resultado or {}
        job.concluido_em = datetime.utcnow()
        _aplicar_resultado(db, job)
    else:
        # Volta para a fila até 3 tentativas; depois marca erro definitivo
        job.erro = payload.erro
        job.status = "na_fila" if job.tentativas < 3 else "erro"
        if job.status == "erro" and job.tipo == "analise_ia":
            intimacao = db.query(Intimacao).filter(
                Intimacao.id == (job.payload or {}).get("intimacao_id")
            ).first()
            if intimacao:
                intimacao.status = "erro"
                intimacao.erros = (payload.erro or "análise falhou no agente")[:2000]

    # Se este job pertence a uma execução de workflow (Cérebro), propaga o
    # resultado (node_results + libera Jobs filhos), na mesma transação.
    if job.workflow_execution_id:
        workflow_engine.advance_on_job_complete(db, job)

    db.commit()
    return {"id": job.id, "status": job.status}


def _aplicar_resultado(db: Session, job: Job):
    """Efeitos colaterais de um job concluído — só aqui o sistema registra
    fatos (PDF baixado, protocolo real) porque agora eles existem de verdade."""
    resultado = job.resultado or {}

    if job.tipo in ("esaj_download", "eproc_download") and resultado.get("pdf_path"):
        processo_id = (job.payload or {}).get("processo_id")
        if processo_id:
            db.add(Intimacao(
                processo_id=processo_id,
                origem="esaj",
                tipo="autos",
                assunto=f"Autos baixados do ESAJ ({(job.payload or {}).get('tribunal', '')})",
                pdf_path=resultado["pdf_path"],
                status="pendente",
                source_system="esaj",
                external_id=str(job.id),
            ))

    elif job.tipo == "protocolo" and resultado.get("protocolo_numero"):
        cartao_id = (job.payload or {}).get("cartao_id")
        cartao = db.query(KanbanCartao).filter(KanbanCartao.id == cartao_id).first()
        if cartao:
            cartao.protocolo_numero = resultado["protocolo_numero"]
            cartao.protocolado_em = datetime.utcnow()
            cartao.status_revisao = "protocolado"
        # atualiza o item da fila de protocolo, se houver
        item_id = (job.payload or {}).get("item_protocolo_id")
        if item_id:
            from app.models import ItemProtocolo
            item = db.query(ItemProtocolo).filter(ItemProtocolo.id == item_id).first()
            if item:
                item.protocolo_numero = resultado["protocolo_numero"]
                item.status = "protocolado"

    elif job.tipo == "gerar_laudo" and resultado.get("markdown"):
        # mac_agent gerou o rascunho no Ollama — materializa versão + DOCX
        from app.models import Laudo, LaudoVersao
        from app.services import laudo_exporter
        laudo_id = (job.payload or {}).get("laudo_id")
        laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
        if laudo:
            numero_versao = db.query(LaudoVersao).filter(
                LaudoVersao.laudo_id == laudo_id
            ).count() + 1
            db.add(LaudoVersao(
                laudo_id=laudo_id,
                numero_versao=numero_versao,
                conteudo_markdown=resultado["markdown"],
                gerado_por="qwen-mac",
            ))
            db.flush()
            # RAG: enfileira indexação do laudo para busca semântica futura
            db.add(Job(tipo="indexar_rag", status="na_fila", payload={
                "origem": "laudo", "ref_id": laudo_id, "texto": resultado["markdown"]}))
            docx_path = None
            try:
                export = laudo_exporter.exportar_e_assinar(laudo_id=laudo_id, db=db)
                docx_path = export.get("docx_path")
            except Exception as e:
                job.erro = f"laudo salvo, mas exportação DOCX falhou: {e}"[:2000]
            # libera o protocolo do laudo com o arquivo para o A3
            if docx_path:
                dependentes = db.query(Job).filter(
                    Job.tipo == "protocolo_laudo", Job.status == "na_fila"
                ).all()
                for dep in dependentes:
                    if (dep.payload or {}).get("aguardar_job_id") == job.id:
                        novo_payload = dict(dep.payload or {})
                        novo_payload["arquivo_path"] = docx_path
                        dep.payload = novo_payload

    elif job.tipo == "protocolo_oficio" and resultado.get("protocolo_numero"):
        from app.models import Oficio
        oficio = db.query(Oficio).filter(
            Oficio.id == (job.payload or {}).get("oficio_id")
        ).first()
        if oficio:
            oficio.numero_protocolo = str(resultado["protocolo_numero"])
            oficio.status = "protocolado"

    elif job.tipo == "protocolo_laudo" and resultado.get("protocolo_numero"):
        from app.models import Laudo
        laudo = db.query(Laudo).filter(
            Laudo.id == (job.payload or {}).get("laudo_id")
        ).first()
        if laudo:
            laudo.status = "protocolado"

    elif job.tipo == "esaj_intimacoes":
        # cada PDF baixado do ESAJ vira uma intimação pendente (a IA analisa depois)
        for item in resultado.get("intimacoes", []):
            cnj = item.get("numero_cnj")
            if not cnj:
                continue
            processo = db.query(Processo).filter(Processo.numero_cnj == cnj).first()
            if not processo:
                processo = Processo(numero_cnj=cnj, titulo=f"Processo {cnj}",
                                    status="ativo", source_system="esaj")
                db.add(processo)
                db.flush()
            # dedup: mesmo PDF não cria intimação duplicada
            ja = db.query(Intimacao).filter(
                Intimacao.source_system == "esaj",
                Intimacao.external_id == item.get("pdf_path"),
            ).first()
            if ja:
                continue
            db.add(Intimacao(
                processo_id=processo.id, origem="esaj", tipo="intimacao",
                assunto=f"Intimação ESAJ — {cnj}", pdf_path=item.get("pdf_path"),
                status="pendente", source_system="esaj",
                external_id=item.get("pdf_path"),
            ))

    elif job.tipo == "esaj_sincronizar":
        # Sincronização automática de autos — marca processo como baixado
        numero_cnj = (job.payload or {}).get("numero_cnj")
        if numero_cnj:
            processo = db.query(Processo).filter(
                Processo.numero_cnj == numero_cnj
            ).first()
            if processo:
                processo.esaj_autos_baixado = True
                # Se resultado contém PDF path, registra intimação
                if resultado.get("pdf_path"):
                    db.add(Intimacao(
                        processo_id=processo.id,
                        origem="esaj",
                        tipo="autos",
                        assunto=f"Autos ESAJ — {numero_cnj}",
                        pdf_path=resultado["pdf_path"],
                        status="pendente",
                        source_system="esaj",
                        external_id=f"esaj_sincronizar:{job.id}",
                    ))

    elif job.tipo == "analise_ia" and resultado.get("dados"):
        intimacao = db.query(Intimacao).filter(
            Intimacao.id == (job.payload or {}).get("intimacao_id")
        ).first()
        if intimacao:
            intimacao.dados_estruturados = resultado["dados"]
            intimacao.status = "analisada"
            intimacao.erros = None
            # propaga partes/vara/juiz para o cadastro do processo vinculado
            from app.services import vinculo
            proc = db.query(Processo).filter(Processo.id == intimacao.processo_id).first()
            if proc:
                vinculo.propagar(proc, resultado["dados"])

    elif job.tipo == "analisar_captacao":
        from app.models import Oportunidade
        for a in resultado.get("analises", []):
            djen_id = a.get("djen_id")
            if not djen_id or db.query(Oportunidade).filter(Oportunidade.djen_id == djen_id).first():
                continue
            sem = float(a.get("merito_sem_pct") or 0)
            com = float(a.get("merito_com_pct") or 0)
            # score: ganho que a perícia traz, penalizado por lead ruim
            score = (com - sem)
            if a.get("defensoria"):
                score -= 50
            if a.get("empresa_grande"):
                score -= 20
            if a.get("oab_antiga"):
                score += 10
            if not a.get("oportunidade", True):
                score -= 30
            db.add(Oportunidade(
                djen_id=djen_id, tribunal=a.get("tribunal"), numero_processo=a.get("numero_processo"),
                area=a.get("area"), oportunidade=bool(a.get("oportunidade", True)),
                defensoria=bool(a.get("defensoria")), empresa_grande=bool(a.get("empresa_grande")),
                oab_antiga=bool(a.get("oab_antiga")), advogado_nome=a.get("advogado_nome"),
                advogado_oab=a.get("advogado_oab"), advogado_email=a.get("advogado_email"),
                merito_sem_pct=sem or None, merito_com_pct=com or None,
                ressalvas=a.get("ressalvas"), resumo=a.get("resumo"), score=score,
                texto=a.get("texto"), link=a.get("link"),
            ))
        db.commit()

    elif job.tipo == "rascunho_email_captacao" and resultado.get("email"):
        from app.models import Oportunidade
        o = db.query(Oportunidade).filter(
            Oportunidade.id == (job.payload or {}).get("oportunidade_id")).first()
        if o:
            o.email_rascunho = resultado["email"]


@router.get("/{job_id}/arquivo")
async def baixar_arquivo_job(
    job_id: int,
    db: Session = Depends(get_db),
    _=Depends(verificar_agente),
):
    """Serve o PDF referenciado no payload do job para o agente Mac analisar."""
    import os
    from fastapi.responses import FileResponse

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    caminho = (job.payload or {}).get("pdf_path") or (job.payload or {}).get("arquivo_path")
    if not caminho or not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Job sem arquivo ou arquivo inexistente")
    return FileResponse(caminho, media_type="application/octet-stream")


@router.get("/{job_id}")
async def obter_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@router.patch("/{job_id}/heartbeat")
async def job_heartbeat(
    job_id: int,
    db: Session = Depends(get_db),
    _=Depends(verificar_agente),
):
    """
    PATCH /api/v1/jobs/{job_id}/heartbeat

    Agente reporta que está ainda processando o job (heartbeat).
    Atualiza last_heartbeat para o timestamp atual.
    Isto previne que o job seja marcado como órfão pelo admin/scheduler.

    Resposta:
    {
        "id": job_id,
        "status": "processando",
        "last_heartbeat": "2026-07-16T15:00:00"
    }
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    if job.status != "processando":
        logger.warning(f"Job {job_id} com heartbeat mas status={job.status}")
        return {
            "id": job.id,
            "status": job.status,
            "warning": f"Job não está em 'processando' (status atual: {job.status})",
        }

    job.last_heartbeat = datetime.utcnow()
    db.commit()

    return {
        "id": job.id,
        "status": "processando",
        "last_heartbeat": job.last_heartbeat.isoformat(),
    }
