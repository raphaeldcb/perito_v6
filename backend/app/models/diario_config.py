"""Configuração do monitoramento do Diário Oficial (DJEN) — termos a incluir na
busca (nome do escritório/peritos/especialidades) e termos a excluir (ruído)."""
from sqlalchemy import Column, Integer
from app.models.types import JSONBType
from .base import Base, TimestampMixin


class DiarioConfig(Base, TimestampMixin):
    __tablename__ = "diario_config"

    id = Column(Integer, primary_key=True, default=1)
    incluir = Column(JSONBType)     # ["INSTITUTO DE PERICIAS CIENTIFICAS", "IPC MS", ...]
    excluir = Column(JSONBType)     # termos que descartam a publicação
    tribunais = Column(JSONBType)   # ["TJMS", "TJMT", ...]
