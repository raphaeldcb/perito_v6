"""AssistProduction: classificação de atividade (produtivo / ocioso / suspeito).

Duas camadas, por custo/latência:

1. Heurística (síncrona, grátis, roda na ingestão): casa `app_ativo` contra
   listas de palavras-chave. Cobre >95% dos casos (Word/Excel/PJe = produtivo,
   YouTube/Netflix/jogo = suspeito, tela travada/sem input = ocioso já vem
   marcado pelo agente). Isso sozinho já preenche o requisito "produtivo/
   ocioso/suspeito" sem gastar 1 token de LLM em 8.640 eventos/dia/device.

2. Qwen (assíncrona, via fila de Job — igual esaj_download/analise_ia):
   só para os casos "suspeito" da heurística, 1x/dia por device, o Qwen local
   (Ollama no Mac, mesmo modelo perito-qwen do resto do sistema) dá um
   parecer contextual (padrão de uso ao longo do dia, não só o nome do app)
   e uma justificativa em português para o gestor. Resultado fica no próprio
   Job.resultado (reaproveita a tabela `job` como analysis_result — não cria
   tabela nova pra isso, é exatamente o padrão de esaj_intimacoes/analise_ia).

Nada aqui infere ociosidade "de verdade" — só reclassifica o app em foco.
O tempo ativo/ocioso continua vindo 100% do agente (mouse/teclado), que é
o único que sabe se o colaborador estava interagindo.
"""
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AssistProductionEvento, Job, User

logger = logging.getLogger(__name__)

# Palavras-chave em minúsculo, casadas por substring no título da janela/app
# ativo reportado pelo agente (ex: "YouTube - Google Chrome", "WhatsApp").
PALAVRAS_PRODUTIVO = (
    "word", "excel", "powerpoint", "outlook", "teams", "onedrive",
    "sistema.ipcms", "pje", "esaj", "eproc", "projuris", "acrobat", "pdf",
    "explorer", "visual studio", "vscode", "notepad", "chrome - sistema",
    "edge - sistema", "docusign", "safeweb", "websigner",
)
PALAVRAS_SUSPEITO = (
    "youtube", "netflix", "prime video", "disney+", "twitch", "spotify",
    "steam", "epic games", "jogo", "game", "facebook", "instagram",
    "tiktok", "twitter", "x.com", "bet365", "betano", "blaze", "aposta",
    "torrent", "utorrent", "xvideos", "pornhub",
)
# neutro: WhatsApp/e-mail pessoal, navegação genérica etc. — não penaliza nem
# credita; some vira ativo "sem classificação" no dashboard.


def classificar_heuristico(app_ativo: str | None) -> str:
    """Retorna 'produtivo' | 'suspeito' | 'neutro' a partir do app/site em foco.

    Não decide 'ocioso' — isso é telemetria do agente (mouse/teclado), não do
    nome do app. Um app "produtivo" aberto sem interação já vira 'ocioso' no
    tipo do evento antes mesmo de chegar aqui."""
    if not app_ativo:
        return "neutro"
    alvo = app_ativo.lower()
    if any(p in alvo for p in PALAVRAS_SUSPEITO):
        return "suspeito"
    if any(p in alvo for p in PALAVRAS_PRODUTIVO):
        return "produtivo"
    return "neutro"


def detectar_e_enfileirar_suspeitos(db: Session, data_ref: date, max_por_device: int = 1) -> int:
    """Varre os eventos 'ativo' do dia com app_ativo suspeito pela heurística e
    enfileira NO MÁXIMO 1 Job de análise Qwen por device/dia (custo controlado
    — o Mac roda 1 Ollama, não precisamos de 1 chamada por evento).

    Executado pelo scheduler noturno logo após agregar_dia(). Idempotente:
    não duplica se já existe um Job 'analise_produtividade' pendente/feito
    para o mesmo device na mesma data."""
    inicio = datetime.combine(data_ref, datetime.min.time())
    fim = inicio + timedelta(days=1)

    eventos = (
        db.query(AssistProductionEvento)
        .filter(
            AssistProductionEvento.timestamp >= inicio,
            AssistProductionEvento.timestamp < fim,
            AssistProductionEvento.tipo == "ativo",
        )
        .all()
    )

    por_device: dict[str, list[AssistProductionEvento]] = {}
    for ev in eventos:
        if classificar_heuristico(ev.app_ativo) == "suspeito":
            por_device.setdefault(ev.device_id, []).append(ev)

    enfileirados = 0
    for device_id, evs in por_device.items():
        ja_existe = (
            db.query(Job)
            .filter(
                Job.tipo == "analise_produtividade",
                Job.payload["device_id"].astext == device_id,
                Job.payload["data"].astext == data_ref.isoformat(),
            )
            .first()
        )
        if ja_existe:
            continue

        usuario = db.query(User).filter(User.device_id == device_id).first()
        # agrupa por app pra não mandar 500 linhas repetidas pro prompt
        por_app: dict[str, int] = {}
        for ev in evs:
            por_app[ev.app_ativo or "?"] = por_app.get(ev.app_ativo or "?", 0) + (ev.duracao_segundos or 0)

        db.add(Job(
            tipo="analise_produtividade",
            status="na_fila",
            payload={
                "device_id": device_id,
                "data": data_ref.isoformat(),
                "usuario_id": usuario.id if usuario else None,
                "usuario_nome": usuario.full_name if usuario else None,
                "apps_suspeitos": [
                    {"app": app, "duracao_segundos": seg} for app, seg in
                    sorted(por_app.items(), key=lambda x: -x[1])[:20]
                ],
            },
        ))
        enfileirados += 1
        if enfileirados >= max_por_device:
            pass  # max_por_device é por device (sempre 1 aqui); loop já é por device

    if enfileirados:
        db.commit()
        logger.info(f"AssistProduction: {enfileirados} job(s) de análise Qwen enfileirados para {data_ref}")
    return enfileirados


def listar_analises(db: Session, limit: int = 50) -> list[dict]:
    """Lê o resultado das análises Qwen já concluídas (Job como analysis_result
    — mesmo padrão de esaj_intimacoes, sem tabela nova)."""
    jobs = (
        db.query(Job)
        .filter(Job.tipo == "analise_produtividade")
        .order_by(Job.id.desc())
        .limit(limit)
        .all()
    )
    saida = []
    for j in jobs:
        payload = j.payload or {}
        resultado = j.resultado or {}
        saida.append({
            "job_id": j.id,
            "status": j.status,
            "device_id": payload.get("device_id"),
            "usuario_nome": payload.get("usuario_nome"),
            "data": payload.get("data"),
            "classificacao": resultado.get("classificacao"),
            "justificativa": resultado.get("justificativa"),
            "apps_analisados": [a["app"] for a in payload.get("apps_suspeitos", [])],
        })
    return saida
