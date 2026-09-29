"""Despesa (conta a pagar) extraída dos PDFs de DESPESAS — módulo financeiro/BPO."""
from sqlalchemy import Column, Integer, SmallInteger, String, Date, Numeric, Text, Boolean
from app.models.base import Base, TimestampMixin


class Despesa(Base, TimestampMixin):
    __tablename__ = "despesa"

    id = Column(Integer, primary_key=True)
    fornecedor = Column(String(200))
    data = Column(Date)
    vencimento = Column(Date, nullable=True)
    valor = Column(Numeric(12, 2))
    descricao = Column(Text)
    categoria = Column(String(40))                 # aluguel, energia, salario, imposto...
    status = Column(String(20), default="a_pagar")  # a_pagar | pago
    arquivo_path = Column(String(500), unique=True, index=True)  # dedup
    ano = Column(SmallInteger, index=True)
    mes = Column(SmallInteger)
    pago = Column(Boolean, default=False)
    origem = Column(String(30))                    # despesas_folder/despesas_gerais/recorrente/manual
    origem_ref = Column(String(200))
    recorrencia = Column(String(20), default="avulsa")   # avulsa | mensal
    forma_pagamento = Column(String(20))                 # dinheiro/cartao_credito/cartao_debito/pix/cheque
    conta = Column(String(10), default="ipc")            # ipc | externo
    tem_nf = Column(Boolean, nullable=True)
