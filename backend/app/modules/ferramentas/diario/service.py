# v6/backend/app/modules/ferramentas/{tool}/service.py
"""
Diario (DJEN) Service Layer — Isolates business logic from routing.

Thin wrapper around app.services.diario_djen for module isolation.
"""

from sqlalchemy.orm import Session
from app.services import diario_djen


class DiarioService:
    """Business logic for DJEN (Diário Oficial) operations."""

    @staticmethod
    def get_config(db: Session):
        """Retrieve current DJEN search configuration."""
        cfg = diario_djen._config(db)
        return {
            "incluir": cfg.incluir or [],
            "excluir": cfg.excluir or [],
            "tribunais": cfg.tribunais or diario_djen.TRIBUNAIS_PADRAO,
            "tribunais_disponiveis": diario_djen.TRIBUNAIS_PADRAO
        }

    @staticmethod
    def save_config(db: Session, incluir: list[str], excluir: list[str], tribunais: list[str]):
        """Save DJEN search configuration."""
        cfg = diario_djen._config(db)
        cfg.incluir = [t.strip() for t in incluir if t.strip()]
        cfg.excluir = [t.strip() for t in excluir if t.strip()]
        cfg.tribunais = tribunais or diario_djen.TRIBUNAIS_PADRAO
        db.commit()
        return {"ok": True}

    @staticmethod
    def consultar(tribunais: list[str], incluir: list[str], excluir: list[str], dias: int = 7):
        """Execute one-off DJEN search (config-independent)."""
        pubs = diario_djen.consultar(tribunais, incluir, excluir, dias)
        return {"total": len(pubs), "publicacoes": pubs}

    @staticmethod
    def sincronizar(db: Session):
        """Run DJEN search using saved config and save new opportunities."""
        novas = diario_djen.consultar_e_salvar(db)
        return {"novas": novas}


__all__ = ["DiarioService"]
