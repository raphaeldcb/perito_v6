"""DEPRECATED: Conciliação (moved to modules/ferramentas/conciliacao).

This module is kept for backward compatibility only. All functionality has been moved to:
    app.modules.ferramentas.conciliacao.service

Please update imports to use the new module location:
    from app.modules.ferramentas.conciliacao import service
    service.fator_correcao(...)
    service.corrigir(...)
    service.conciliar_credito(...)

This file will be removed in a future version.
"""
import warnings
from app.modules.ferramentas.conciliacao import service

warnings.warn(
    "app.services.conciliacao_valor is deprecated. Use app.modules.ferramentas.conciliacao.service instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
fator_correcao = service.fator_correcao
corrigir = service.corrigir
conciliar_credito = service.conciliar_credito

__all__ = ["fator_correcao", "corrigir", "conciliar_credito"]
