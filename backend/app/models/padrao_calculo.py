"""Padrão de cálculo salvo — um conjunto de critérios reutilizável.
Ex: "Poupança até a sentença, IPCA depois" (timeline + base + tese + multa).

Os 3 campos `regra_semantica`/`tokens_encontrados`/`validacao_oficial` foram
adicionados à tabela em `backend/migrations/2026_08_03_calculo_v2_tables.sql`
(Task 3 do plano calculo_v2) para suportar padrões semânticos com tokens
([SENTENÇA], [CITAÇÃO] etc — ver app/services/padroes_semanticos.py, Task 7)
que a Task 8 resolve em datas reais lendo o PDF oficial via Qwen."""
from sqlalchemy import Boolean, Column, Integer, String, Text
from app.models.types import JSONBType
from .base import Base, TimestampMixin


class PadraoCalculo(Base, TimestampMixin):
    __tablename__ = "padrao_calculo"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer)
    nome = Column(String(120), nullable=False)
    config = Column(JSONBType)   # {timeline, base_dias, tese, multa_pct}

    # Padrão semântico (Task 7/8): regra em texto com tokens de marco
    # processual, ex: "Poupança até [SENTENÇA], IPCA depois".
    regra_semantica = Column(Text)
    tokens_encontrados = Column(JSONBType)  # cache de tokenizar_regra(regra_semantica)
    validacao_oficial = Column(Boolean, default=False)  # True só após confirmação do perito contra o PDF oficial
