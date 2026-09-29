"""Dashboard — Stats, charts, aggregations em tempo real do banco."""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.middleware import get_current_user
from app.models import User, Processo, Intimacao
from app.services import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _do_usuario(user: User):
    """Filtro de visibilidade de processo no dashboard.

    Os 188 processos importados do legado ficaram com `responsavel_id` NULL
    (conferido em produção: COUNT(*)=188, COUNT(responsavel_id)=0). Filtrando só
    por `responsavel_id == user.id`, NENHUM batia — o dashboard dava 0 pra todos e
    o acervo inteiro ficava invisível, junto com as 138 intimações penduradas nele.

    Processo sem responsável é acervo do escritório e aparece pra quem está logado;
    processo de OUTRO usuário continua invisível (isolamento preservado). Assim o
    dashboard também não volta a zerar se uma importação futura esquecer o dono.
    """
    return or_(Processo.responsavel_id == user.id, Processo.responsavel_id.is_(None))

# ─────────────────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    meus_processos: int
    receita: float
    taxa_conclusao: int
    intimacoes_pendentes: int

class ChartPoint(BaseModel):
    label: str
    value: float

class ReceitaPoint(BaseModel):
    mes: str
    valor: float

# ─────────────────────────────────────────────────────────────
# @GET /api/v1/dashboard/stats
# ─────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    periodo: str = Query("month", description="month|all"),
    setor: str = Query(""),
    status: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retorna stats principais: processos, receita, conclusão, tempo médio."""

    # Filtros comuns — montados uma vez e reaproveitados nas 3 queries abaixo,
    # senão elas divergem (era o caso: receita ignorava o filtro de período).
    filtros = [_do_usuario(user)]
    if setor:
        filtros.append(Processo.setor == setor)
    if status:
        filtros.append(Processo.status == status)
    if periodo == "month":
        filtros.append(Processo.created_at >= datetime.utcnow() - timedelta(days=30))

    q = db.query(Processo).filter(*filtros)

    # Stats
    meus_processos = q.count()

    # Receita (mesmos filtros)
    receita = db.query(func.sum(Processo.honorarios)).filter(*filtros).scalar() or 0.0

    # Taxa conclusão (% que tem status='Concluído') - apenas com os filtros atuais
    concluidos = q.filter(Processo.status == "Concluído").count()
    taxa_conclusao = (concluidos * 100 // meus_processos) if meus_processos > 0 else 0

    # Intimações pendentes (REAL: status='pendente' nos processos visíveis)
    intimacoes_pendentes = (
        db.query(func.count(Intimacao.id))
        .join(Processo, Intimacao.processo_id == Processo.id)
        .filter(*filtros, Intimacao.status == "pendente")
        .scalar()
    ) or 0

    return StatsResponse(
        meus_processos=meus_processos,
        receita=float(receita),
        taxa_conclusao=taxa_conclusao,
        intimacoes_pendentes=int(intimacoes_pendentes),
    )

# ─────────────────────────────────────────────────────────────
# @GET /api/v1/dashboard/receita-mes
# ─────────────────────────────────────────────────────────────

@router.get("/receita-mes", response_model=list[ReceitaPoint])
async def get_receita_mes(
    meses: int = Query(12, description="últimos N meses"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Receita por mês (últimos N meses)."""
    # Era SQL cru com `INTERVAL ':meses months'`: o :meses estava DENTRO de uma
    # string literal, então nunca era bindado — o banco recebia o texto ':meses'
    # e a query explodia. Além disso TO_CHAR/NOW() são específicos de Postgres.
    # Agregar em Python resolve os dois (o volume é de centenas de linhas).
    desde = datetime.utcnow() - timedelta(days=31 * meses)

    rows = (
        db.query(Processo.created_at, Processo.honorarios)
        .filter(_do_usuario(user), Processo.created_at >= desde)
        .all()
    )

    por_mes = defaultdict(float)
    for created_at, honorarios in rows:
        if created_at is None:
            continue
        por_mes[created_at.strftime("%Y-%m")] += float(honorarios or 0)

    return [ReceitaPoint(mes=mes, valor=por_mes[mes]) for mes in sorted(por_mes)]

# ─────────────────────────────────────────────────────────────
# @GET /api/v1/dashboard/volume-especialidade
# ─────────────────────────────────────────────────────────────

@router.get("/volume-especialidade", response_model=list[ChartPoint])
async def get_volume_especialidade(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Volume de processos por especialidade."""
    q = db.query(
        Processo.setor.label("label"),
        func.count(Processo.id).label("value")
    ).filter(_do_usuario(user)).group_by(Processo.setor)

    return [ChartPoint(label=row.label or "Sem setor", value=row.value) for row in q]

# ─────────────────────────────────────────────────────────────
# @GET /api/v1/dashboard/conclusao-timeline
# ─────────────────────────────────────────────────────────────

@router.get("/conclusao-timeline", response_model=list[ChartPoint])
async def get_conclusao_timeline(
    semanas: int = Query(4, description="últimas N semanas"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """% de processos concluídos por semana (últimas N semanas)."""
    # Mesmo problema do /receita-mes: ':semanas' dentro de string literal (nunca
    # bindado) + TO_CHAR/NOW() só de Postgres. Agregado em Python.
    desde = datetime.utcnow() - timedelta(weeks=semanas)

    rows = (
        db.query(Processo.created_at, Processo.status)
        .filter(_do_usuario(user), Processo.created_at >= desde)
        .all()
    )

    totais = defaultdict(int)
    concluidos = defaultdict(int)
    for created_at, status in rows:
        if created_at is None:
            continue
        semana = created_at.strftime("%Y-%W")
        totais[semana] += 1
        if status == "Concluído":
            concluidos[semana] += 1

    return [
        ChartPoint(label=semana, value=round(100.0 * concluidos[semana] / totais[semana]))
        for semana in sorted(totais)
    ]

# ─────────────────────────────────────────────────────────────
# @GET /api/v1/dashboard/status-distribuicao
# ─────────────────────────────────────────────────────────────

@router.get("/status-distribuicao", response_model=list[ChartPoint])
async def get_status_distribuicao(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Distribuição de processos por status (pie chart)."""
    q = db.query(
        Processo.status.label("label"),
        func.count(Processo.id).label("value")
    ).filter(_do_usuario(user)).group_by(Processo.status)

    return [ChartPoint(label=row.label or "Sem status", value=row.value) for row in q]
