"""Integração Banco Inter — contas, transações, Pix, boletos, cobranças.

Fluxo:
1. OAuth2: Sistema conecta com Inter usando client_credentials
2. Webhook: Inter notifica Perito de eventos (Pix recebido, boleto emitido, etc)
3. Reconciliação: Transações da Inter casam com lançamento_bancario (automático)
4. Pagamentos: Sistema cria pagamento, Bruno autoriza no app Inter, webhook confirma
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Boolean, ForeignKey, Enum
from app.models.types import JSONBType
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.mixins import TimestampMixin
import enum


class InterAccount(Base, TimestampMixin):
    """Conta Inter vinculada ao Perito."""
    __tablename__ = "inter_account"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="CASCADE"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    # OAuth2
    access_token = Column(String(500), nullable=False)  # Bearer token (CRIPTOGRAFAR!)
    refresh_token = Column(String(500), nullable=True)
    token_expira_em = Column(DateTime, nullable=True)
    scope = Column(String(500))  # scopes autorizados

    # Inter account info
    conta_numero = Column(String(20))  # Número da conta
    agencia = Column(String(10))       # Agência
    cnpj = Column(String(14))          # CNPJ da conta
    saldo = Column(Numeric(12, 2))     # Cache do saldo (atualizar via API)

    # Webhooks
    webhook_secret = Column(String(255))  # Chave para validar assinatura HMAC
    webhook_ativo = Column(Boolean, default=True)

    # Metadata
    meta_info = Column(JSONBType)  # {ambiente: 'producao'|'sandbox', ...}

    empresa = relationship("Empresa")
    usuario = relationship("User")
    transacoes = relationship("InterTransaction", back_populates="conta")
    pixs = relationship("InterPix", back_populates="conta")
    boletos = relationship("InterBoleto", back_populates="conta")
    cobrancas = relationship("InterCobranca", back_populates="conta")


class InterTransaction(Base, TimestampMixin):
    """Transação (movimento) do Inter — sincronizado com lançamento_bancario."""
    __tablename__ = "inter_transaction"

    id = Column(Integer, primary_key=True)
    conta_id = Column(Integer, ForeignKey("inter_account.id", ondelete="CASCADE"), nullable=False)
    lancamento_id = Column(Integer, ForeignKey("lancamento_bancario.id"), nullable=True)

    # Dados do Inter
    inter_id = Column(String(100), unique=True)  # ID da transação no Inter (evita duplicata)
    tipo = Column(String(50))  # credito, debito, transferencia, pix, boleto, etc
    data = Column(DateTime)
    data_contabil = Column(DateTime)  # Data que efetivamente entrou na conta
    valor = Column(Numeric(12, 2))
    descricao = Column(Text)
    historico = Column(Text)

    # Contrapartes
    cpf_cnpj_contrapartida = Column(String(14))
    nome_contrapartida = Column(String(200))

    # Status
    status = Column(String(50))  # confirmado, pendente, revertido
    reconciliado = Column(Boolean, default=False)

    conta = relationship("InterAccount", back_populates="transacoes")


class InterPix(Base, TimestampMixin):
    """Pix — envio/recebimento."""
    __tablename__ = "inter_pix"

    id = Column(Integer, primary_key=True)
    conta_id = Column(Integer, ForeignKey("inter_account.id", ondelete="CASCADE"), nullable=False)

    # Identificador
    pix_id = Column(String(100), unique=True)  # ID da chave Pix no Inter
    tipo_chave = Column(String(50))  # cpf, cnpj, email, telefone, random
    chave = Column(String(100))  # Valor da chave (CPF, email, etc)
    descricao = Column(String(200))

    # Status
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime)
    data_exclusao = Column(DateTime, nullable=True)

    conta = relationship("InterAccount", back_populates="pixs")


class InterBoleto(Base, TimestampMixin):
    """Boleto emitido — com ou sem Pix (QR Code)."""
    __tablename__ = "inter_boleto"

    id = Column(Integer, primary_key=True)
    conta_id = Column(Integer, ForeignKey("inter_account.id", ondelete="CASCADE"), nullable=False)

    # Identificador
    boleto_id = Column(String(100), unique=True)
    nosso_numero = Column(String(20))  # Número do boleto no Inter
    codigo_barras = Column(String(50))

    # Dados
    valor = Column(Numeric(12, 2))
    vencimento = Column(DateTime)
    descricao = Column(Text)

    # Beneficiário (quem recebe)
    cpf_cnpj_beneficiario = Column(String(14))
    nome_beneficiario = Column(String(200))

    # Pix (QR Code) — opcional
    pix_qrcode = Column(Text)  # QR Code base64
    pix_copia_cola = Column(Text)  # String pra copiar

    # Status
    status = Column(String(50))  # emitido, pago, vencido, cancelado
    data_pagamento = Column(DateTime, nullable=True)

    conta = relationship("InterAccount", back_populates="boletos")


class InterCobranca(Base, TimestampMixin):
    """Cobrança — com vencimento ou imediata."""
    __tablename__ = "inter_cobranca"

    id = Column(Integer, primary_key=True)
    conta_id = Column(Integer, ForeignKey("inter_account.id", ondelete="CASCADE"), nullable=False)

    # Identificador
    cobranca_id = Column(String(100), unique=True)

    # Dados
    valor = Column(Numeric(12, 2))
    vencimento = Column(DateTime, nullable=True)  # NULL = cobrança imediata
    descricao = Column(Text)

    # Devedor (quem paga)
    cpf_cnpj_devedor = Column(String(14))
    nome_devedor = Column(String(200))

    # Pix (sempre tem QR Code)
    pix_qrcode = Column(Text)
    pix_copia_cola = Column(Text)

    # Status
    status = Column(String(50))  # emitida, paga, vencida, cancelada, devolvida
    data_pagamento = Column(DateTime, nullable=True)
    motivo_devolucao = Column(Text, nullable=True)

    conta = relationship("InterAccount", back_populates="cobrancas")


class InterWebhook(Base, TimestampMixin):
    """Log de webhooks recebidos do Inter."""
    __tablename__ = "inter_webhook"

    id = Column(Integer, primary_key=True)
    conta_id = Column(Integer, ForeignKey("inter_account.id", ondelete="CASCADE"), nullable=False)

    # Webhook
    tipo_evento = Column(String(100))  # pixRecebido, boletoPago, pagamentoEnviado, etc
    payload = Column(JSONBType)  # Body completo do webhook
    assinatura = Column(String(500))  # HMAC signature (validação)
    validado = Column(Boolean, default=False)  # Assinatura válida?

    # Processamento
    processado = Column(Boolean, default=False)
    erro = Column(Text, nullable=True)
    job_id = Column(Integer, ForeignKey("job.id"), nullable=True)  # Referência ao job que processou
