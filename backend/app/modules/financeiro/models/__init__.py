"""
Financeiro module models — Boleto, Nota, Honorario.

Handles payment management with Banco Inter and Conta Única integration.
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Date, Enum, Text, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
import enum
from datetime import datetime


class BoletoStatus(str, enum.Enum):
    """Status do boleto."""
    CRIADO = "criado"
    EMITIDO = "emitido"
    VENCIDO = "vencido"
    PAGO = "pago"
    CANCELADO = "cancelado"


class Boleto(Base, TimestampMixin):
    """Boleto de cobrança gerado pelo sistema ou Banco Inter."""
    __tablename__ = "boleto"

    id = Column(Integer, primary_key=True)
    numero = Column(String(50), unique=True, nullable=False, index=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False, index=True)

    valor = Column(Numeric(12, 2), nullable=False)
    vencimento = Column(Date, nullable=False, index=True)
    status = Column(String(20), default=BoletoStatus.CRIADO, nullable=False, index=True)

    # Banco Inter integration
    inter_id = Column(String(100), unique=True, nullable=True)  # ID do boleto no Inter
    inter_url = Column(String(500), nullable=True)  # URL para visualizar boleto
    qr_code = Column(Text, nullable=True)  # QR code para Pix cópia e cola

    # Histórico
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_emissao = Column(DateTime, nullable=True)
    data_pagamento = Column(DateTime, nullable=True)
    data_cancelamento = Column(DateTime, nullable=True)

    descricao = Column(String(500), nullable=True)
    juros_multa = Column(Numeric(12, 2), default=0, nullable=False)
    desconto = Column(Numeric(12, 2), default=0, nullable=False)

    # Soft delete
    ativo = Column(Boolean, default=True, nullable=False)

    # Índices para performance
    __table_args__ = (
        Index("idx_boleto_numero", "numero"),
        Index("idx_boleto_processo_id", "processo_id"),
        Index("idx_boleto_status", "status"),
        Index("idx_boleto_vencimento", "vencimento"),
    )

    processo = relationship("Processo")


class Nota(Base, TimestampMixin):
    """Nota fiscal ou recibo de pagamento."""
    __tablename__ = "nota"

    id = Column(Integer, primary_key=True)
    numero = Column(String(50), unique=True, nullable=False, index=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False, index=True)

    valor = Column(Numeric(12, 2), nullable=False)
    descricao = Column(String(500), nullable=False)
    data_emissao = Column(Date, nullable=False, index=True)

    # Fiscal
    nf_serie = Column(String(10), nullable=True)
    nf_numero = Column(String(20), nullable=True)
    nf_emitente = Column(String(200), nullable=True)
    nf_cnpj = Column(String(14), nullable=True)

    # Rastreamento
    url_acesso = Column(String(500), nullable=True)
    chave_acesso = Column(String(44), nullable=True)  # Chave de acesso NF-e

    # Status
    status = Column(String(20), default="pendente", nullable=False, index=True)  # pendente, recebida, arquivada

    # Soft delete
    ativo = Column(Boolean, default=True, nullable=False)

    # Nomes de índice são GLOBAIS no Postgres (e no SQLite), não por tabela.
    # `app/models/nota_fiscal.py` (tabela `nota_fiscal`, a que está em produção)
    # já ocupa `idx_nota_status`, então esta tabela precisa de prefixo próprio —
    # senão `Base.metadata.create_all()` estoura com "index already exists" e a
    # tabela `nota` nunca chega a ser criada.
    __table_args__ = (
        Index("idx_nota_tbl_numero", "numero"),
        Index("idx_nota_tbl_processo_id", "processo_id"),
        Index("idx_nota_tbl_status", "status"),
    )

    processo = relationship("Processo")


class Honorario(Base, TimestampMixin):
    """Honorário de perícia — percentual ou fixo."""
    __tablename__ = "honorario"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False, index=True)

    valor_base = Column(Numeric(12, 2), nullable=False)  # Valor base do processo
    percentual = Column(Numeric(5, 2), nullable=False)  # Percentual de honorário (ex: 10.50)
    valor_final = Column(Numeric(12, 2), nullable=False)  # Valor calculado final

    status_pagamento = Column(String(20), default="pendente", nullable=False, index=True)  # pendente, pago, parcial
    data_pagamento = Column(DateTime, nullable=True)

    # Desconto / Ajuste
    desconto = Column(Numeric(12, 2), default=0, nullable=False)
    acrescimo = Column(Numeric(12, 2), default=0, nullable=False)

    # Observações
    observacoes = Column(Text, nullable=True)

    # Soft delete
    ativo = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_honorario_processo_id", "processo_id"),
        Index("idx_honorario_status_pagamento", "status_pagamento"),
    )

    processo = relationship("Processo")
