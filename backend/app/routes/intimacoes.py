"""Bridge file: re-exports router from isolated module.

Migration complete: intimacoes now lives in app.modules.ferramentas.intimacoes
This file maintains backward compatibility.
"""
from app.modules.ferramentas.intimacoes import router

__all__ = ["router"]
