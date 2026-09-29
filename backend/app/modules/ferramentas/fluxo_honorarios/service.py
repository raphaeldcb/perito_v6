"""Service layer for fluxo_honorarios (honorarium flow) — re-exports existing business logic."""
from app.services.fluxo_honorarios import (
    _slug,
    _slug_juizo,
    historico_juizo,
    proximo_nn,
    decidir_honorarios,
    registrar_atuacao,
    LIMIAR_REDUCAO,
    TEMPLATE,
)
from app.services.oficio_honorarios import (
    gerar_oficio_honorarios,
)

__all__ = [
    "_slug",
    "_slug_juizo",
    "historico_juizo",
    "proximo_nn",
    "decidir_honorarios",
    "registrar_atuacao",
    "gerar_oficio_honorarios",
    "LIMIAR_REDUCAO",
    "TEMPLATE",
]
