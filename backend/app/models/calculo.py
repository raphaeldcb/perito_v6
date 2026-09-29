"""Cálculo persistido (payload + resultado) + vínculo a laudo/proposta/AT +
histórico de versões.

Schema espelha exatamente `backend/migrations/2026_08_03_calculo_v2_tables.sql`
(Task 3 do plano `docs/superpowers/plans/2026_001-ferramenta_calculo_v2.md`) —
mesmos nomes de tabela/coluna (`criado_em`/`atualizado_em`, não o
TimestampMixin padrão do projeto, porque a migration já usa esses nomes).
`Base.metadata.create_all()` (chamado em `init_db()`) cria as tabelas se ainda
não existirem — não duplica a migration solta, só garante que o schema real
bate com o que a migration desenhou.
"""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String,
    Text, UniqueConstraint,
)

from app.models.types import JSONBType
from .base import Base


class Calculo(Base):
    __tablename__ = "calculo"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    processo_id = Column(Integer, ForeignKey("processo.id"))
    payload = Column(JSONBType, nullable=False)
    resultado = Column(JSONBType)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalculoVinculo(Base):
    __tablename__ = "calculo_vinculo"
    __table_args__ = (
        UniqueConstraint("calculo_id", name="uq_calculo_vinculo_calculo_id"),
        CheckConstraint(
            "tipo_vinculo IN ('laudo', 'proposta', 'at')",
            name="ck_calculo_vinculo_tipo",
        ),
    )

    id = Column(Integer, primary_key=True)
    calculo_id = Column(Integer, ForeignKey("calculo.id", ondelete="CASCADE"), nullable=False)
    tipo_vinculo = Column(String(20), nullable=False)  # laudo | proposta | at
    objeto_id = Column(Integer, nullable=False)
    versao = Column(Integer, default=1)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalculoHistorico(Base):
    __tablename__ = "calculo_historico"
    __table_args__ = (
        UniqueConstraint("calculo_id", "versao", name="uq_calculo_historico_versao"),
    )

    id = Column(Integer, primary_key=True)
    calculo_id = Column(Integer, ForeignKey("calculo.id", ondelete="CASCADE"), nullable=False)
    versao = Column(Integer, nullable=False)
    payload = Column(JSONBType, nullable=False)
    resultado_saldo_final = Column(Numeric(15, 2))
    criado_em = Column(DateTime, default=datetime.utcnow)
    criado_por = Column(Integer, ForeignKey("usuario.id"))
    alteracao_descricao = Column(String(255))


class CalculoArvoreDecisao(Base):
    """Auditoria de padrão semântico (Task 8): datas que o Qwen sugeriu ao ler
    o PDF oficial da decisão vs. as que o perito confirmou. `datas_sugeridas`
    nunca é sobrescrita silenciosamente — reaplica o mesmo padrão no mesmo
    processo apenas atualiza a sugestão (UNIQUE padrao_id+processo_id, mesma
    regra do `backend/migrations/2026_08_03_calculo_v2_tables.sql`)."""
    __tablename__ = "calculo_arvore_decisao"
    __table_args__ = (
        UniqueConstraint("padrao_id", "processo_id", name="uq_arvore_decisao_padrao_processo"),
    )

    id = Column(Integer, primary_key=True)
    padrao_id = Column(Integer, ForeignKey("padrao_calculo.id"), nullable=False)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False)
    regra_original = Column(String(500), nullable=False)
    datas_sugeridas = Column(JSONBType)      # {"SENTENÇA": "2020-05-15", ...} — sugestão do Qwen
    datas_confirmadas = Column(JSONBType)    # preenchido quando o perito confirma/corrige
    diferencas = Column(JSONBType)           # sugerido vs confirmado, se divergirem
    ai_interpretacao_texto = Column(Text)    # resposta bruta do Qwen (auditoria)
    confirmado_em = Column(DateTime)
    confirmado_por = Column(Integer, ForeignKey("usuario.id"))
