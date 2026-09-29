"""Configuração da automação diária do ESAJ (horário, ativo)."""
from sqlalchemy import Column, Integer, String, Boolean
from .base import Base, TimestampMixin


class EsajConfig(Base, TimestampMixin):
    __tablename__ = "esaj_config"

    id = Column(Integer, primary_key=True, default=1)
    hora = Column(String(5), default="03:00")   # HH:MM — busca diária de intimações
    ativo = Column(Boolean, default=True)
    ultima_execucao = Column(String(30))         # ISO da última rodada (evita repetir no dia)
