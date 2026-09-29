"""Registro RESILIENTE de routers (never again 2026-07-27).
Um router que falha ao importar (dep faltando, erro de sintaxe) é PULADO com aviso —
NUNCA derruba o app inteiro. Antes: 1 import quebrado (ex: tjms sem playwright) = backend 502.
"""
from fastapi import APIRouter
import importlib
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# (modulo, prefix|None, tags|None) — ordem preservada. prefix None = o router define o seu.
_ROUTERS = [
    ("auth", "/api/v1/auth", ["auth"]),
    ("users", "/api/v1/users", ["users"]),
    ("tools", "/api/v1/tools", ["tools"]),
    ("roles", "/api/v1/roles", ["roles"]),
    ("audit", "/api/v1/audit", ["audit"]),
    ("kanban", "/api/v1/kanban", ["kanban"]),
    ("intimacoes", None, None), ("jobs", None, None), ("importar", None, None),
    ("parametros", None, None), ("esaj", None, None), ("coletadores", None, None),
    ("financeiro", None, None), ("notas", None, None), ("processos", None, None),
    ("engenharia", None, None), ("fluxo_honorarios", None, None), ("conciliacao_valor", None, None),
    ("financeiro_ingest", None, None), ("ferramentas", None, None), ("valores", None, None),
    ("modelos", None, None), ("calculo", None, None), ("diario", None, None),
    ("protocolo", None, None), ("laudos", None, None), ("setup", None, None),
    ("deslocamento_pedagio", None, None), ("dados_processos", None, None), ("fluxo_completo", None, None),
    ("publico", None, None), ("rag", None, None), ("oficios", None, None),
    ("admin", None, None), ("template_versions", None, None), ("inter_api", None, None),
    ("upload_seguro", None, None), ("agent", None, None), ("projetocp", None, None),
    ("cerebro_advanced", "/api/v1/cerebro", ["cerebro"]),
    ("dashboard", None, None), ("dashboard_alertas", None, None), ("delegacao", None, None),
    ("propostas", None, None), ("tjms", None, None), ("gerencia", None, None),
    ("comunicacoes", None, None), ("comunicacoes_auto_resposta", None, None),
]

_carregados, _pulados = [], []
for mod, prefix, tags in _ROUTERS:
    try:
        m = importlib.import_module(f"app.routes.{mod}")
        kw = {}
        if prefix:
            kw["prefix"] = prefix
        if tags:
            kw["tags"] = tags
        router.include_router(m.router, **kw)
        _carregados.append(mod)
    except Exception as e:  # dep faltando / erro de import → PULA, não derruba
        _pulados.append(mod)
        logger.warning(f"[routes] router '{mod}' PULADO ({type(e).__name__}: {str(e)[:100]})")

logger.info(f"[routes] {len(_carregados)} carregados, {len(_pulados)} pulados: {_pulados}")

__all__ = ["router"]
