"""Receita (entrada) canônica — consolida ProjetoCP + CONTROLE FINANCEIRO + antigo."""
from sqlalchemy import Column, Integer, SmallInteger, String, Date, Numeric, Text, Boolean, ForeignKey, UniqueConstraint
from app.models.base import Base, TimestampMixin


class Receita(Base, TimestampMixin):
    __tablename__ = "receita"

    id = Column(Integer, primary_key=True)
    data = Column(Date)
    ano = Column(SmallInteger, nullable=False, index=True)
    mes = Column(SmallInteger)
    setor = Column(String(50), index=True)             # DNA/CON/ENG/GRAF/MULTI/OUTRO/Consultorias/etc
    valor = Column(Numeric(14, 2), nullable=False)
    tipo_pagamento = Column(String(20))                # cartao/pix/dinheiro/judicial/gratuito/inter/outro
    num_pericias = Column(Integer)
    descricao = Column(Text)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=True)
    origem = Column(String(30), nullable=False)        # projetocp/controle_financeiro/financeiro_antigo/manual
    origem_ref = Column(String(120), nullable=True)  # Can be null for imported data
    forma_liquidacao = Column(String(20))              # a_vista/parcelado/conta_unica/ao_final
    forma_pagamento = Column(String(20))               # dinheiro/cartao_credito/cartao_debito/pix/cheque
    conta = Column(String(10), default="ipc")          # ipc | externo
    tem_nf = Column(Boolean, nullable=True)

    __table_args__ = (UniqueConstraint("origem", "origem_ref", name="uq_receita_origem"),)
