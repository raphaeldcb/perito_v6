"""Tipos de coluna cross-dialect (Postgres em produção, SQLite em dev/test local).

Producao roda 100% em PostgreSQL (docker, VPS). Dev local usa SQLite
(`sqlite:///./v6.db`, ver .env/.env.test). `postgresql.JSONB`/`ARRAY` puros
não existem no dialeto SQLite — `Base.metadata.create_all()` quebra o
startup inteiro assim que qualquer model usa esses tipos direto, mesmo que
a rota testada nem toque na tabela.

`with_variant()` resolve isso sem duplicar models: Postgres continua usando
JSONB/ARRAY nativos (índices GIN, operadores @>, etc. se algum dia usarmos),
SQLite cai para JSON genérico (dump/load simples, sem indexação — irrelevante
pra dev local).
"""
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

# Uso: Column(JSONBType) — no lugar de Column(JSONB)
JSONBType = PG_JSONB().with_variant(JSON(), "sqlite")


def ArrayType(item_type):
    """Uso: Column(ArrayType(Float)) — no lugar de Column(ARRAY(Float))."""
    return PG_ARRAY(item_type).with_variant(JSON(), "sqlite")
