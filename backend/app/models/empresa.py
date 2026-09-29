"""Empresas do grupo IPC MS (2) — para vínculo de coletadores e conciliação."""
from sqlalchemy import Column, Integer, String
from .base import Base, TimestampMixin


class Empresa(Base, TimestampMixin):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True)
    razao_social = Column(String(200), nullable=False)
    nome_fantasia = Column(String(120))
    cnpj = Column(String(20), unique=True, nullable=False)
    regime_tributario = Column(String(60))  # Lucro Presumido, Simples Nacional
    banco = Column(String(120))              # ex: Inter (conta Pesquisa)
