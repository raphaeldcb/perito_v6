# v6/backend/app/modules/ferramentas/intimacoes/__init__.py
from .router import router
from .schemas import *
from . import service

__all__ = ["router", "service"]
