"""
Diario (DJEN) — Diário Oficial Legal Journal Monitoring Schemas.

Public DTOs for inter-module communication and API contracts.
"""

from pydantic import BaseModel


class ConfigInput(BaseModel):
    """Configuration input for DJEN search settings."""
    incluir: list[str] = []
    excluir: list[str] = []
    tribunais: list[str] = []


class ConsultaInput(BaseModel):
    """Consulta (one-off search) input for DJEN publications."""
    incluir: list[str] = []
    excluir: list[str] = []
    tribunais: list[str] = []
    dias: int = 7


class AnalisarInput(BaseModel):
    """Análise (opportunity scoring) input for publications."""
    publicacoes: list[dict]


__all__ = [
    "ConfigInput",
    "ConsultaInput",
    "AnalisarInput",
]
