"""
Rotas para sincronização automática de autos ESAJ — PARALELO 3.

Endpoints:
  POST   /api/v1/esaj/sincronizar           — enfileira jobs para lista de CNJs
  GET    /api/v1/esaj/sincronizar-status/{job_id}  — consulta status de um job
  GET    /api/v1/esaj/sincronizar-stats    — estatísticas agregadas
  GET    /api/v1/esaj/sincronizar-listagem  — lista jobs com paginação

Integra-se com:
  - Sistema de fila de jobs (Job model)
  - Tabela Processo (marca esaj_autos_baixado = true ao completar)
  - Tabela Intimacao (registra PDF baixado como tipo="autos")
  - Graph Email (já existente no /api/v1/esaj)
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.middleware import get_current_user
from app.models import User, Job, Processo, Intimacao
from app.routes.jobs import verificar_agente
from app.services import get_db
import logging
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/esaj", tags=["esaj"])
logger = logging.getLogger(__name__)


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class SincronizarInput(BaseModel):
    """Payload para POST /api/v1/esaj/sincronizar"""
    cnjs: Optional[list[str]] = Field(
        None,
        description="Lista de CNJs a sincronizar. Se vazio, usa BD (processos atrasados)"
    )
    tribunal: str = Field("TJMS", description="Tribunal: TJMS, TJMT, etc.")
    limpar_existentes: bool = Field(
        False,
        description="Se True, marca esaj_autos_baixado=false antes de enfileirar"
    )


class SincronizarResponse(BaseModel):
    """Response do POST"""
    total: int = Field(description="Total de CNJs a sincronizar")
    enfileirados: int = Field(description="Quantidade de jobs criados")
    job_ids: list[int] = Field(description="IDs dos jobs para polling")
    msg: str = Field(description="Mensagem descritiva")


class JobStatusResponse(BaseModel):
    """Response do GET /sincronizar-status/{job_id}"""
    id: int
    tipo: str
    status: str
    numero_cnj: Optional[str] = None
    tribunal: Optional[str] = None
    tentativas: int
    iniciado_em: Optional[datetime] = None
    concluido_em: Optional[datetime] = None
    resultado: Optional[dict] = None
    erro: Optional[str] = None


class SincronizarStatsResponse(BaseModel):
    """Response do GET /sincronizar-stats"""
    periodo: str
    desde: datetime
    total: int
    concluido: int
    erro: int
    processando: int
    na_fila: int
    taxa_sucesso_pct: float


class SincronizarItemResponse(BaseModel):
    """Item da listagem"""
    id: int
    numero_cnj: Optional[str]
    status: str
    tribunal: Optional[str]
    tentativas: int
    criado_em: datetime


# ============================================================================
# ROTAS
# ============================================================================

@router.post("/sincronizar", response_model=SincronizarResponse)
async def sincronizar_autos(
    payload: SincronizarInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SincronizarResponse:
    """
    Enfileira download de autos para lista de CNJs.

    Se payload.cnjs estiver vazio, lê processos "ativo" do BD com mesmo tribunal.
    Para cada CNJ, cria job tipo "esaj_sincronizar".

    Exemplo (linha de comando):
    ```
    curl -X POST http://localhost:8000/api/v1/esaj/sincronizar \\
      -H "Authorization: Bearer $JWT" \\
      -H "Content-Type: application/json" \\
      -d '{"cnjs": ["0000058-68.2025.8.24.3731"], "tribunal": "TJMS"}'
    ```

    Response:
    ```json
    {
      "total": 1,
      "enfileirados": 1,
      "job_ids": [999],
      "msg": "Jobs 999 a 999 enfileirados para processamento"
    }
    ```
    """

    # Determinar lista de CNJs
    if payload.cnjs:
        cnjs = payload.cnjs
        log_origem = f"parâmetro (n={len(cnjs)})"
    else:
        # Ler do BD: processos ativos do tribunal
        processos = db.query(Processo).filter(
            Processo.status == "ativo",
            Processo.tribunal == payload.tribunal,
        ).all()
        cnjs = [p.numero_cnj for p in processos]
        log_origem = f"BD (tribunal={payload.tribunal}, n={len(cnjs)})"

    if not cnjs:
        raise HTTPException(
            status_code=400,
            detail=f"Nenhum CNJ encontrado (origem: {log_origem})"
        )

    logger.info(f"🔄 Sincronizando {len(cnjs)} CNJs ({log_origem})")

    # Opcionalmente limpar flag anterior
    if payload.limpar_existentes:
        db.query(Processo).filter(
            Processo.numero_cnj.in_(cnjs)
        ).update(
            {"esaj_autos_baixado": False},
            synchronize_session=False
        )
        logger.info(f"   🔄 Flag esaj_autos_baixado resetado para {len(cnjs)} processos")

    # Enfileirar jobs
    job_ids = []
    for cnj in cnjs:
        job = Job(
            tipo="esaj_sincronizar",
            payload={
                "numero_cnj": cnj,
                "tribunal": payload.tribunal,
                "enfileirado_em": datetime.utcnow().isoformat(),
            },
            status="na_fila",
        )
        db.add(job)
        db.flush()
        job_ids.append(job.id)

    db.commit()
    logger.info(f"✅ {len(job_ids)} jobs enfileirados (IDs: {job_ids[0]}...{job_ids[-1]})")

    return SincronizarResponse(
        total=len(cnjs),
        enfileirados=len(job_ids),
        job_ids=job_ids,
        msg=f"Jobs {job_ids[0]} a {job_ids[-1]} enfileirados para processamento"
    )


@router.get("/sincronizar-status/{job_id}", response_model=JobStatusResponse)
async def consultar_status_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobStatusResponse:
    """
    Consulta status de um job específico.

    Permite polling do progresso de um job enfileirado.

    Exemplo:
    ```
    curl http://localhost:8000/api/v1/esaj/sincronizar-status/999 \\
      -H "Authorization: Bearer $JWT"
    ```

    Response:
    ```json
    {
      "id": 999,
      "tipo": "esaj_sincronizar",
      "status": "processando",
      "numero_cnj": "0000058-68.2025.8.24.3731",
      "tribunal": "TJMS",
      "tentativas": 1,
      "iniciado_em": "2026-07-17T14:30:00",
      "concluido_em": null,
      "resultado": null,
      "erro": null
    }
    ```
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return JobStatusResponse(
        id=job.id,
        tipo=job.tipo,
        status=job.status,
        numero_cnj=(job.payload or {}).get("numero_cnj"),
        tribunal=(job.payload or {}).get("tribunal"),
        tentativas=job.tentativas,
        iniciado_em=job.iniciado_em,
        concluido_em=job.concluido_em,
        resultado=job.resultado or {},
        erro=job.erro,
    )


@router.get("/sincronizar-stats", response_model=SincronizarStatsResponse)
async def obter_stats_sincronizacao(
    periodo: str = Query("today", regex="^(today|week|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SincronizarStatsResponse:
    """
    Retorna estatísticas de sincronização por período.

    Períodos:
      - today: último 1 dia
      - week: últimos 7 dias
      - all: toda história

    Exemplo:
    ```
    curl "http://localhost:8000/api/v1/esaj/sincronizar-stats?periodo=today" \\
      -H "Authorization: Bearer $JWT"
    ```

    Response:
    ```json
    {
      "periodo": "today",
      "desde": "2026-07-17T00:00:00",
      "total": 188,
      "concluido": 45,
      "erro": 2,
      "processando": 15,
      "na_fila": 126,
      "taxa_sucesso_pct": 23.9
    }
    ```
    """
    query = db.query(Job).filter(Job.tipo == "esaj_sincronizar")

    if periodo == "today":
        desde = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "week":
        desde = datetime.utcnow() - timedelta(days=7)
    else:
        desde = datetime.utcnow() - timedelta(days=365)

    query = query.filter(Job.criado_em >= desde)

    total = query.count()
    concluido = query.filter(Job.status == "concluido").count()
    erro = query.filter(Job.status == "erro").count()
    processando = query.filter(Job.status == "processando").count()
    na_fila = query.filter(Job.status == "na_fila").count()

    taxa_sucesso = (concluido / total * 100) if total > 0 else 0.0

    return SincronizarStatsResponse(
        periodo=periodo,
        desde=desde,
        total=total,
        concluido=concluido,
        erro=erro,
        processando=processando,
        na_fila=na_fila,
        taxa_sucesso_pct=round(taxa_sucesso, 2),
    )


@router.get("/sincronizar-listagem", response_model=list[SincronizarItemResponse])
async def listar_sincronizacoes(
    status_filtro: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SincronizarItemResponse]:
    """
    Lista jobs de sincronização com paginação.

    Parâmetros:
      - status_filtro: filtrar por status (na_fila, processando, concluido, erro)
      - limit: número de registros (1-500, default 50)
      - offset: deslocamento (paginação, default 0)

    Exemplo:
    ```
    curl "http://localhost:8000/api/v1/esaj/sincronizar-listagem?status_filtro=erro&limit=10" \\
      -H "Authorization: Bearer $JWT"
    ```

    Response:
    ```json
    [
      {
        "id": 999,
        "numero_cnj": "0000058-68.2025.8.24.3731",
        "status": "erro",
        "tribunal": "TJMS",
        "tentativas": 3,
        "criado_em": "2026-07-17T14:30:00"
      }
    ]
    ```
    """
    query = db.query(Job).filter(Job.tipo == "esaj_sincronizar")

    if status_filtro:
        query = query.filter(Job.status == status_filtro)

    jobs = query.order_by(Job.id.desc()).offset(offset).limit(limit).all()

    return [
        SincronizarItemResponse(
            id=j.id,
            numero_cnj=(j.payload or {}).get("numero_cnj"),
            status=j.status,
            tribunal=(j.payload or {}).get("tribunal"),
            tentativas=j.tentativas,
            criado_em=j.criado_em,
        )
        for j in jobs
    ]


# ============================================================================
# INTEGRAÇÃO COM JOBS (modificar app/routes/jobs.py)
# ============================================================================

"""
⚠️  MODIFICAÇÃO NECESSÁRIA em app/routes/jobs.py:

Na função _aplicar_resultado(), adicione este bloco:

    elif job.tipo == "esaj_sincronizar":
        # Job de sincronização automática — marca processo como baixado
        numero_cnj = (job.payload or {}).get("numero_cnj")
        if numero_cnj:
            processo = db.query(Processo).filter(
                Processo.numero_cnj == numero_cnj
            ).first()
            if processo:
                processo.esaj_autos_baixado = True

                # Se o resultado contém caminho do PDF, registrar intimação
                if resultado.get("pdf_path"):
                    db.add(Intimacao(
                        processo_id=processo.id,
                        origem="esaj",
                        tipo="autos",
                        assunto=f"Autos TJMS — {numero_cnj}",
                        pdf_path=resultado["pdf_path"],
                        status="pendente",
                        source_system="esaj",
                        external_id=f"esaj_sincronizar:{job.id}",
                    ))
"""
