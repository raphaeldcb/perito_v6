"""Cache dos índices oficiais do Banco Central (API SGS), persistido no BD.

Atualizado automaticamente a cada 10 dias pelo worker — não depende de rede na
hora do cálculo e sobrevive a restart.
"""
from sqlalchemy import Column, String, DateTime
from app.models.types import JSONBType
from .base import Base, TimestampMixin


class IndiceCache(Base, TimestampMixin):
    __tablename__ = "indice_cache"

    indexador = Column(String(20), primary_key=True)   # IPCA, SELIC, INPC...
    valores = Column(JSONBType)                             # {"AAAA-MM": pct}
    atualizado_em = Column(DateTime)
