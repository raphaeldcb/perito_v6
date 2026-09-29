"""AssistProduction ↔ Financeiro: custo_hora, agregação diária e alertas.

Modelo de custo (definido no escopo da tarefa):
    custo_hora = (salario_mensal ou honorario_mensal) / 160h
    custo_desperdicado = (tempo_ocioso_segundos / 3600) * custo_hora

160h é jornada padrão (CLT ~44h/semana ~= 190h; usamos 160h porque é o valor
pedido no escopo — se a IPC quiser trocar por jornada real, isso vira
parâmetro em `Parametro` (chave 'produtividade_horas_mes'), não hardcode).
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AssistProductionEvento, AssistProductionFinanceiroSummary, Parametro, User

logger = logging.getLogger(__name__)

HORAS_MES_PADRAO = Decimal("160")
CHAVE_HORAS_MES = "produtividade_horas_mes"
CHAVE_THRESHOLD = "produtividade_alerta_threshold"           # R$ a partir do qual dispara alerta
CHAVE_WHATSAPP_WEBHOOK = "whatsapp_webhook_url"               # ex: Z-API/Evolution API endpoint
CHAVE_WHATSAPP_TOKEN = "whatsapp_token"
CHAVE_WHATSAPP_NUMERO_DESTINO = "whatsapp_numero_destino"     # nº do gestor que recebe o alerta


def _parametro(db: Session, chave: str, default: str = "") -> str:
    p = db.query(Parametro).filter(Parametro.chave == chave).first()
    return p.valor if p and p.valor else default


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return v if isinstance(v, Decimal) else Decimal(str(v))


def horas_mes(db: Session) -> Decimal:
    txt = _parametro(db, CHAVE_HORAS_MES, "")
    if not txt:
        return HORAS_MES_PADRAO
    try:
        return Decimal(txt)
    except Exception:
        return HORAS_MES_PADRAO


def custo_hora_usuario(usuario: User, base_horas_mes: Decimal = HORAS_MES_PADRAO) -> Decimal:
    """custo_hora = base_mensal / horas_mes. base_mensal = salário OU honorário
    (o que estiver preenchido; se os dois estiverem, usa salário — é o vínculo
    empregatício formal). Sem nenhum dos dois preenchido, custo_hora = 0 e o
    tempo ocioso desse colaborador não gera custo (falta de cadastro, não
    "grátis" — aparece sinalizado no dashboard)."""
    if usuario is None:
        return Decimal("0")
    base = _dec(usuario.salario_mensal) or _dec(usuario.honorario_mensal)
    if base <= 0 or base_horas_mes <= 0:
        return Decimal("0")
    return (base / base_horas_mes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def registrar_eventos(db: Session, device_id: str, eventos: list[dict]) -> int:
    """Ingestão bruta do agente AssistProduction. Resolve usuario_id pelo
    device_id cadastrado em usuario.device_id (se o evento não trouxer
    usuario_id explícito). Idempotente por natureza — cada POST é um lote
    novo de intervalos, não há upsert por chave natural aqui (a agregação
    diária que dedup/soma)."""
    usuario = db.query(User).filter(User.device_id == device_id).first()
    usuario_id_default = usuario.id if usuario else None

    criados = 0
    for ev in eventos:
        ts_raw = ev.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else ts_raw
        except Exception:
            logger.warning(f"Evento AssistProduction com timestamp inválido ignorado: {ts_raw}")
            continue

        tipo = (ev.get("tipo") or "").lower()
        if tipo not in ("ativo", "ocioso"):
            logger.warning(f"Evento AssistProduction com tipo inválido ignorado: {ev.get('tipo')}")
            continue

        db.add(AssistProductionEvento(
            device_id=device_id,
            usuario_id=ev.get("usuario_id") or usuario_id_default,
            timestamp=ts,
            tipo=tipo,
            duracao_segundos=int(ev.get("duracao_segundos") or 0),
            app_ativo=ev.get("app_ativo"),
        ))
        criados += 1

    db.commit()
    return criados


def agregar_dia(db: Session, data_ref: date) -> dict:
    """Agrega todos os eventos da data_ref, por device_id, calcula custo e faz
    upsert em assistproduction_financeiro_summary. Executado pelo scheduler
    noturno (D-1) e disponível sob demanda para backfill/teste via API admin.

    Idempotente: pode rodar de novo para a mesma data (recalcula do zero a
    partir dos eventos brutos, não acumula em cima do summary anterior)."""
    inicio = datetime.combine(data_ref, datetime.min.time())
    fim = inicio + timedelta(days=1)
    base_horas = horas_mes(db)

    eventos = (
        db.query(AssistProductionEvento)
        .filter(AssistProductionEvento.timestamp >= inicio, AssistProductionEvento.timestamp < fim)
        .all()
    )

    if not eventos:
        return {"data": data_ref.isoformat(), "devices_processados": 0, "eventos": 0}

    por_device: dict[str, dict] = {}
    for ev in eventos:
        agg = por_device.setdefault(ev.device_id, {
            "usuario_id": ev.usuario_id, "ativo_s": 0, "ocioso_s": 0,
        })
        if ev.tipo == "ativo":
            agg["ativo_s"] += ev.duracao_segundos or 0
        else:
            agg["ocioso_s"] += ev.duracao_segundos or 0
        # se algum evento do lote trouxer usuario_id e o agg ainda não tiver, usa
        if not agg["usuario_id"] and ev.usuario_id:
            agg["usuario_id"] = ev.usuario_id

    threshold = _dec(_parametro(db, CHAVE_THRESHOLD, "500.00") or "500.00")
    alertas_disparados = []

    for device_id, agg in por_device.items():
        usuario = db.query(User).get(agg["usuario_id"]) if agg["usuario_id"] else None
        c_hora = custo_hora_usuario(usuario, base_horas)
        custo = ((_dec(agg["ocioso_s"]) / Decimal("3600")) * c_hora).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        summary = (
            db.query(AssistProductionFinanceiroSummary)
            .filter(
                AssistProductionFinanceiroSummary.device_id == device_id,
                AssistProductionFinanceiroSummary.data == data_ref,
            )
            .first()
        )
        if summary is None:
            summary = AssistProductionFinanceiroSummary(device_id=device_id, data=data_ref)
            db.add(summary)

        summary.usuario_id = agg["usuario_id"]
        summary.tempo_ativo_segundos = agg["ativo_s"]
        summary.tempo_desperdicado_segundos = agg["ocioso_s"]
        summary.custo_hora = c_hora
        summary.custo_desperdicado = custo

        db.flush()  # garante summary.id antes do alerta

        if custo >= threshold and not summary.alerta_enviado:
            nome = usuario.full_name if usuario else f"device {device_id}"
            enviado = enviar_alerta_whatsapp(db, nome, custo, data_ref)
            if enviado:
                summary.alerta_enviado = True
                summary.alerta_enviado_em = datetime.utcnow()
                alertas_disparados.append(nome)

    db.commit()

    return {
        "data": data_ref.isoformat(),
        "devices_processados": len(por_device),
        "eventos": len(eventos),
        "alertas_disparados": alertas_disparados,
    }


def enviar_alerta_whatsapp(db: Session, colaborador_nome: str, custo: Decimal, data_ref: date) -> bool:
    """Dispara alerta via webhook WhatsApp (Z-API/Evolution API/Twilio — qualquer
    gateway que aceite POST {number, message}). Configuração fica em Parametro
    (categoria 'whatsapp'): whatsapp_webhook_url, whatsapp_token,
    whatsapp_numero_destino. Sem essas 3 chaves preenchidas, não envia nada e
    só loga — não existe WhatsApp real conectado ainda, isso é o contrato de
    integração pronto para quando o gateway for contratado."""
    webhook = _parametro(db, CHAVE_WHATSAPP_WEBHOOK)
    token = _parametro(db, CHAVE_WHATSAPP_TOKEN)
    numero = _parametro(db, CHAVE_WHATSAPP_NUMERO_DESTINO)

    mensagem = (
        f"⚠️ Alerta de produtividade — {data_ref.strftime('%d/%m/%Y')}\n"
        f"Colaborador {colaborador_nome} gerou R$ {custo:.2f} de desperdício hoje "
        f"(tempo ocioso monitorado pelo AssistProduction)."
    )

    if not (webhook and numero):
        logger.warning(
            "WhatsApp não configurado (whatsapp_webhook_url/whatsapp_numero_destino "
            f"em Parametro) — alerta NÃO enviado, só logado: {mensagem}"
        )
        return False

    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = requests.post(
            webhook, json={"number": numero, "message": mensagem}, headers=headers, timeout=10
        )
        resp.raise_for_status()
        logger.info(f"Alerta WhatsApp enviado: {colaborador_nome} / R$ {custo:.2f}")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar alerta WhatsApp para {colaborador_nome}: {e}")
        return False


def obter_custos(db: Session, periodo: str = "dia", usuario_id: int | None = None) -> dict:
    """Lê assistproduction_financeiro_summary agregado pelo período pedido.
    periodo: 'dia' (hoje), 'semana' (últimos 7 dias), 'mes' (últimos 30 dias).
    """
    hoje = date.today()
    janelas = {"dia": 1, "semana": 7, "mes": 30}
    dias = janelas.get(periodo, 1)
    data_inicio = hoje - timedelta(days=dias - 1)

    q = db.query(
        AssistProductionFinanceiroSummary.usuario_id,
        func.sum(AssistProductionFinanceiroSummary.tempo_ativo_segundos).label("ativo_s"),
        func.sum(AssistProductionFinanceiroSummary.tempo_desperdicado_segundos).label("ocioso_s"),
        func.sum(AssistProductionFinanceiroSummary.custo_desperdicado).label("custo"),
    ).filter(AssistProductionFinanceiroSummary.data >= data_inicio, AssistProductionFinanceiroSummary.data <= hoje)

    if usuario_id:
        q = q.filter(AssistProductionFinanceiroSummary.usuario_id == usuario_id)

    q = q.group_by(AssistProductionFinanceiroSummary.usuario_id)

    por_colaborador = []
    total_custo = Decimal("0")
    total_ocioso_s = 0
    for usuario_id_row, ativo_s, ocioso_s, custo in q.all():
        usuario = db.query(User).get(usuario_id_row) if usuario_id_row else None
        custo = _dec(custo)
        total_custo += custo
        total_ocioso_s += ocioso_s or 0
        por_colaborador.append({
            "usuario_id": usuario_id_row,
            "nome": usuario.full_name if usuario else "(device sem colaborador vinculado)",
            "tempo_ativo_segundos": ativo_s or 0,
            "tempo_desperdicado_segundos": ocioso_s or 0,
            "custo_desperdicado": float(custo),
        })

    por_colaborador.sort(key=lambda r: r["custo_desperdicado"], reverse=True)

    # série diária (para o gráfico) — soma de todos os colaboradores por dia
    serie = (
        db.query(
            AssistProductionFinanceiroSummary.data,
            func.sum(AssistProductionFinanceiroSummary.custo_desperdicado).label("custo"),
            func.sum(AssistProductionFinanceiroSummary.tempo_desperdicado_segundos).label("ocioso_s"),
        )
        .filter(AssistProductionFinanceiroSummary.data >= data_inicio, AssistProductionFinanceiroSummary.data <= hoje)
        .group_by(AssistProductionFinanceiroSummary.data)
        .order_by(AssistProductionFinanceiroSummary.data)
        .all()
    )

    return {
        "periodo": periodo,
        "data_inicio": data_inicio.isoformat(),
        "data_fim": hoje.isoformat(),
        "total_custo_desperdicado": float(total_custo),
        "total_tempo_desperdicado_segundos": total_ocioso_s,
        "por_colaborador": por_colaborador,
        "serie_diaria": [
            {"data": d.isoformat(), "custo": float(_dec(c)), "tempo_desperdicado_segundos": s or 0}
            for d, c, s in serie
        ],
    }
