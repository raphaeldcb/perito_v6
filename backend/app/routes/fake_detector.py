"""Re-export router from modules — keeps routes/__init__.py pattern."""
from app.modules.ferramentas.fake_detector import router

__all__ = ["router"]
