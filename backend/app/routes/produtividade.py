"""AssistProduction ↔ Financeiro.

- Ingestão de eventos: agente AssistProduction (X-Agent-Key, igual jobs.py).
- Consulta de custos: usuário logado (JWT). Admin/power_user veem todo mundo;
  usuário comum só vê o próprio custo (não expõe salário de terceiros).
"""
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User
from app.routes.jobs import verificar_agente
from app.services import get_db
from app.services.produtividade_financeiro import (
    registrar_eventos, obter_custos, agregar_dia,
)
from app.services.produtividade_qwen import listar_analises
from app.workers.produtividade_scheduler import (
    obter_estado_scheduler, executar_agregacao_agora,
)

router = APIRouter(prefix="/api/v1/produtividade", tags=["produtividade"])
logger = logging.getLogger(__name__)


def exigir_admin_ou_power(user: User = Depends(get_current_user)) -> User:
    if user.role.name not in ("admin", "power_user"):
        raise HTTPException(status_code=403, detail="Sem permissão para ver produtividade de outros colaboradores")
    return user


class EventoAssistProduction(BaseModel):
    timestamp: str  # ISO 8601
    tipo: str       # 'ativo' | 'ocioso'
    duracao_segundos: int
    app_ativo: str | None = None
    usuario_id: int | None = None  # opcional — normalmente resolvido via device_id


class EventosPayload(BaseModel):
    device_id: str
    eventos: list[EventoAssistProduction]


class AgregarPayload(BaseModel):
    data: str | None = None  # YYYY-MM-DD; default = ontem


@router.post("/eventos")
def ingerir_eventos(payload: EventosPayload, db: Session = Depends(get_db), _=Depends(verificar_agente)):
    """Ingestão bruta do agente AssistProduction rodando no device do colaborador."""
    if not payload.eventos:
        raise HTTPException(status_code=400, detail="Lista de eventos vazia")

    criados = registrar_eventos(db, payload.device_id, [e.model_dump() for e in payload.eventos])
    return {"device_id": payload.device_id, "eventos_registrados": criados}


@router.post("/agregar")
def agregar_agora(payload: AgregarPayload, db: Session = Depends(get_db), _=Depends(exigir_admin_ou_power)):
    """Trigger manual de agregação (backfill/teste). O job noturno já faz isso
    sozinho para D-1 — use isto só para reprocessar uma data específica."""
    try:
        data_ref = datetime.strptime(payload.data, "%Y-%m-%d").date() if payload.data else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida, use YYYY-MM-DD")

    resultado = agregar_dia(db, data_ref) if data_ref else executar_agregacao_agora()
    return resultado


@router.get("/custos")
def custos(
    periodo: str = "dia",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Custo de tempo ocioso por colaborador. periodo: dia | semana | mes.

    Admin/power_user: vê todos os colaboradores.
    Usuário comum: vê só o próprio (não expõe salário/custo de terceiros).
    """
    if periodo not in ("dia", "semana", "mes"):
        raise HTTPException(status_code=400, detail="periodo deve ser dia, semana ou mes")

    is_gestor = user.role.name in ("admin", "power_user")
    usuario_id = None if is_gestor else user.id

    return obter_custos(db, periodo=periodo, usuario_id=usuario_id)


@router.get("/scheduler/status")
def status_scheduler(_=Depends(exigir_admin_ou_power)):
    return obter_estado_scheduler()


@router.get("/analises")
def analises_qwen(
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(exigir_admin_ou_power),
):
    """Pareceres do Qwen (mac_agent) sobre apps 'suspeitos' detectados pela
    heurística — 1 por device/dia, só quando há algo fora do padrão.
    Reaproveita a fila `job` como analysis_result (mesmo padrão de
    esaj_intimacoes/analise_ia), sem tabela nova."""
    return {"analises": listar_analises(db, limit=limit)}
