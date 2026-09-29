"""Índice customizado — o perito cria um indexador manual (ex: Acordo Coletivo X)
e digita os percentuais mês a mês. Persistido para reuso."""
from sqlalchemy import Column, Integer, String
from app.models.types import JSONBType
from .base import Base, TimestampMixin


class IndiceCustomizado(Base, TimestampMixin):
    __tablename__ = "indice_customizado"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer)
    nome = Column(String(120), nullable=False)
    valores = Column(JSONBType)   # {"AAAA-MM": pct, ...}
