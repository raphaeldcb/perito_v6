"""Schemas for Processo and Intimacao modules."""

from .processo_schema import (
    ProcessoCreateSchema,
    ProcessoUpdateSchema,
    ProcessoResponseSchema,
    ProcessoListSchema,
)
from .intimacao_schema import (
    IntimacaoCreateSchema,
    IntimacaoUpdateSchema,
    IntimacaoResponseSchema,
    IntimacaoListSchema,
)

__all__ = [
    # Processo schemas
    "ProcessoCreateSchema",
    "ProcessoUpdateSchema",
    "ProcessoResponseSchema",
    "ProcessoListSchema",
    # Intimacao schemas
    "IntimacaoCreateSchema",
    "IntimacaoUpdateSchema",
    "IntimacaoResponseSchema",
    "IntimacaoListSchema",
]
