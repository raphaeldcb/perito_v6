from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.services.database import get_db
from app.services.feature_flag_service import feature_flag_service


def require_feature_flag(feature_name: str):
    async def dependency(db: Session = Depends(get_db)):
        if not feature_flag_service.is_enabled(feature_name, db):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Feature '{feature_name}' está em manutenção"
            )
        return db

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Se db não está nos kwargs, não fazer nada (será injetado por FastAPI)
            return await func(*args, **kwargs)
        # Adicionar dependência ao wrapper
        wrapper.__signature__ = func.__signature__
        return wrapper

    return decorator
