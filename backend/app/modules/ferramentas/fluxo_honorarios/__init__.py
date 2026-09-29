"""Fluxo Honorários — Honorarium flow module.

Responsável por: gerar ofícios (proposta/ratifica/declina), registrar histórico de juízos,
e acompanhar o ciclo de decisão de honorários.
"""
from .router import router
from .service import (
    decidir_honorarios,
    registrar_atuacao,
    gerar_oficio_honorarios,
    _slug_juizo,
    proximo_nn,
)

__all__ = [
    "router",
    "decidir_honorarios",
    "registrar_atuacao",
    "gerar_oficio_honorarios",
    "_slug_juizo",
    "proximo_nn",
]
