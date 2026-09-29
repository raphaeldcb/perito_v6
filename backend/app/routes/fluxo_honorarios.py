"""Router compatibility wrapper — imports from isolated module.

This file is kept for backwards compatibility with the dynamic router loader.
The actual implementation lives in app.modules.ferramentas.fluxo_honorarios.

Import from the router submodule directly to avoid importing ferramentas/__init__.py
which has pydantic issues from other submodules.
"""
from app.modules.ferramentas.fluxo_honorarios.router import router

__all__ = ["router"]
