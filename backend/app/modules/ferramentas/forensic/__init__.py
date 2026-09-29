# v6/backend/app/modules/ferramentas/forensic/__init__.py
from .router import router
from .schemas import *
from .service import ForensicService

__all__ = ["router", "ForensicService"]
