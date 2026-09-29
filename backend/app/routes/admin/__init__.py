from fastapi import APIRouter
from . import feature_flags

# Combinar todos os sub-routers em um router principal
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# Incluir sub-routers
if hasattr(feature_flags, 'router'):
    router.include_router(feature_flags.router)

__all__ = ['router']
