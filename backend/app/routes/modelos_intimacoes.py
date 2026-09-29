"""Bridge file: modelos_intimacoes routes integrated into intimacoes module.

Migration complete: modelos endpoints are now in app.modules.ferramentas.intimacoes.router
This file is kept for backward compatibility (though no longer used in routes/__init__.py).
"""
from app.modules.ferramentas.intimacoes import router

__all__ = ["router"]
