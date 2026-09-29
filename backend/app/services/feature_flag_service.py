from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.feature_flag import FeatureFlag


class FeatureFlagService:
    def __init__(self):
        self._cache = {}
        self._cache_time = None
        self._cache_ttl = 60

    def _refresh_cache(self, db: Session):
        now = datetime.utcnow()
        if not self._cache_time or (now - self._cache_time).seconds > self._cache_ttl:
            flags = db.query(FeatureFlag).all()
            self._cache = {flag.nome: flag.ativo for flag in flags}
            self._cache_time = now

    def is_enabled(self, feature_name: str, db: Session) -> bool:
        self._refresh_cache(db)
        return self._cache.get(feature_name, False)

    def get_all_flags(self, db: Session) -> dict:
        self._refresh_cache(db)
        return self._cache.copy()

    def set_flag(self, feature_name: str, ativo: bool, db: Session):
        flag = db.query(FeatureFlag).filter(FeatureFlag.nome == feature_name).first()
        if flag:
            flag.ativo = ativo
            db.commit()
            self._cache[feature_name] = ativo
        return flag


feature_flag_service = FeatureFlagService()
