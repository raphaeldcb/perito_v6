"""
ProjetoCP Phase 2: Financial Models (Honorários, Recebimentos, Parcelamento)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, JSON, Numeric, Enum, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from .base import Base, TimestampMixin
import enum


class FinanceiroTipo(str, enum.Enum):
    """Tipo de lançamento financeiro"""
    HONORARIO_LAUDO = "honorario_laudo"
    HONORARIO_SUCUMBENCIA = "honorario_sucumbencia"
    CUSTAS_JUDICIAIS = "custas_judiciais"
    REEMBOLSO_DESPESA = "reembolso_despesa"
    COMISSAO_BANCA = "comissao_banca"
    MULTA_CONTRACTUAL = "multa_contractual"


class FinanceiroStatus(str, enum.Enum):
    """Status do lançamento financeiro"""
    PENDENTE = "pendente"  # Ainda não venceu
    VENCIDO = "vencido"  # Prazo passou sem pagamento
    EM_COBRANCA = "em_cobranca"  # Notificação/protesto enviado
    PARCIALMENTE_PAGO = "parcialmente_pago"
    PAGO = "pago"  # 100% recebido
    CANCELADO = "cancelado"  # Abdicação, acordo
    PRESCRITO = "prescrito"  # Prazo legal esgotado


class Financeiro(Base, TimestampMixin):
    """Lançamento financeiro (fatura) vinculado ao processo/laudo"""
    __tablename__ = "financeiro"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False)
    laudo_id = Column(Integer, ForeignKey("laudo.id"), nullable=True)  # Se é honorário de laudo
    tipo = Column(String(50), nullable=False)  # ENUM FinanceiroTipo
    descricao = Column(Text, nullable=True)  # "Perícia em Grafotécnica - Processo 001/2026"
    valor_bruto = Column(Numeric(12, 2), nullable=False)  # Antes de descontos/taxas
    valor_desconto = Column(Numeric(12, 2), default=0)  # Valor do desconto (se houver)
    valor_liquido = Column(Numeric(12, 2), nullable=False)  # = bruto - desconto (o que recebe)
    moeda = Column(String(5), default="BRL")

    # Datas críticas
    data_emissao = Column(DateTime, default=datetime.utcnow)
    data_vencimento = Column(DateTime, nullable=False)  # Data devida
    data_recebimento_prevista = Column(DateTime, nullable=True)  # Agendada com cliente
    data_primeiro_recebimento = Column(DateTime, nullable=True)  # Real, primeira parcela

    # Indexação (SELIC, IPCA, TR)
    indexador = Column(String(20), default="SELIC")  # SELIC, IPCA, TR, nenhum
    indice_valor_inicial = Column(Numeric(10, 5), nullable=True)  # Valor do índice na emissão
    juros_mora_percentual = Column(Numeric(5, 2), default=1.0)  # % ao mês (padrão 1%)

    # Status
    status = Column(String(30), default="pendente")  # ENUM FinanceiroStatus
    motivo_cancelamento = Column(String(255), nullable=True)  # Se cancelado
    cliente_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)  # Quem pediu
    responsavel_cobranca_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    # Referência externa (integração com nota fiscal, RPS, etc)
    numero_nfse = Column(String(30), nullable=True)
    numero_rps = Column(String(30), nullable=True)
    referencia_externa = Column(String(100), nullable=True)  # ID de sistema externo

    # JSON para campos dinâmicos/futuro
    config_json = Column(JSON, nullable=True)  # {"forma_pagamento_esperada": "deposito", ...}

    # Soft-delete
    ativo = Column(Boolean, default=True, nullable=False)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)

    # Relacionamentos
    processo = relationship("Processo", backref="financeiros")
    laudo = relationship("Laudo", backref="financeiro_lançamentos")
    pagamentos = relationship("Pagamento", back_populates="financeiro", cascade="all, delete-orphan")
    parcelas = relationship("ParcelaFinanceira", back_populates="financeiro", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_financeiro_processo", "processo_id"),
        Index("idx_financeiro_laudo", "laudo_id"),
        Index("idx_financeiro_status", "status"),
        Index("idx_financeiro_vencimento", "data_vencimento"),
    )


class Pagamento(Base, TimestampMixin):
    """Registro de recebimento (1 ou mais por Financeiro se parcelado)"""
    __tablename__ = "pagamento"

    id = Column(Integer, primary_key=True)
    financeiro_id = Column(Integer, ForeignKey("financeiro.id", ondelete="CASCADE"), nullable=False)
    parcela_numero = Column(Integer, default=1)  # 1, 2, 3... (se parcelado)
    data_pagamento = Column(DateTime, default=datetime.utcnow)
    data_comprovacao = Column(DateTime, nullable=True)  # Quando vimos o dinheiro chegar
    valor_recebido = Column(Numeric(12, 2), nullable=False)
    metodo_pagamento = Column(String(50), nullable=False)  # deposito, transferencia, cheque, dinheiro, etc
    banco_recebimento = Column(String(120), nullable=True)  # Qual conta recebeu (IPC, PJ, etc)
    referencia_banco = Column(String(100), nullable=True)  # NSU, DOC, TED, cheque nº
    comprovante_path = Column(String(500), nullable=True)  # Screenshot do comprovante

    # Custódia: se dinheiro recebido mas ainda não processado
    em_custódia = Column(Boolean, default=False)
    custódia_motivo = Column(String(255), nullable=True)  # "Aguardando transferência interna"
    custódia_data_liberacao = Column(DateTime, nullable=True)

    # Reconciliação
    reconciliado = Column(Boolean, default=False)
    reconciliado_em = Column(DateTime, nullable=True)
    lancamento_bancario_id = Column(Integer, nullable=True)  # FK para lancamento_bancario da conciliação

    # Notas e auditoria
    nota = Column(Text, nullable=True)
    recebido_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    processado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    # Soft-delete
    ativo = Column(Boolean, default=True, nullable=False)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)

    financeiro = relationship("Financeiro", back_populates="pagamentos")

    __table_args__ = (
        Index("idx_pagamento_financeiro", "financeiro_id"),
        Index("idx_pagamento_data", "data_pagamento"),
    )


class ParcelaFinanceira(Base, TimestampMixin):
    """Plano de parcelamento de um lançamento financeiro"""
    __tablename__ = "parcela_financeira"

    id = Column(Integer, primary_key=True)
    financeiro_id = Column(Integer, ForeignKey("financeiro.id", ondelete="CASCADE"), nullable=False)
    numero_parcela = Column(Integer, nullable=False)  # 1, 2, 3...
    valor_parcela = Column(Numeric(12, 2), nullable=False)
    data_vencimento = Column(DateTime, nullable=False)
    data_pagamento_efetivo = Column(DateTime, nullable=True)
    status = Column(String(30), default="pendente")  # pendente, pago, vencido, cancelado
    juros_calculados = Column(Numeric(12, 2), default=0)
    multa_atraso = Column(Numeric(12, 2), default=0)  # 2% padrão sobre o valor

    # Vinculação com pagamento real (1:1)
    pagamento_id = Column(Integer, ForeignKey("pagamento.id", ondelete="SET NULL"), nullable=True)

    # Soft-delete
    ativo = Column(Boolean, default=True, nullable=False)
    deletado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)

    financeiro = relationship("Financeiro", back_populates="parcelas")

    __table_args__ = (
        Index("idx_parcela_financeiro", "financeiro_id"),
        Index("idx_parcela_numero", "financeiro_id", "numero_parcela"),
    )


class FinanceiroConfiguracao(Base, TimestampMixin):
    """Configurações globais de financeiro (juros, prazos, etc)"""
    __tablename__ = "financeiro_configuracao"

    id = Column(Integer, primary_key=True, default=1)  # Singleton
    # Juros e multa
    juros_mora_percentual = Column(Numeric(5, 2), default=1.0)  # % ao mês
    multa_atraso_percentual = Column(Numeric(5, 2), default=2.0)  # % do valor
    dias_tolerancia_atraso = Column(Integer, default=0)  # Antes de marcar vencido

    # Parcelamento automático
    ativa_parcelamento_automatico = Column(Boolean, default=True)
    num_parcelas_padrao = Column(Integer, default=1)
    dias_entre_parcelas = Column(Integer, default=30)

    # Indices padrão
    indexador_padrao = Column(String(20), default="SELIC")

    # Alertas
    dias_antes_vencer_alerta = Column(Integer, default=7)
    dias_apos_vencer_notificacao = Column(Integer, default=3)

    # Cobrança
    ativa_cobranca_automatica = Column(Boolean, default=True)
    max_tentativas_cobranca = Column(Integer, default=3)

    __table_args__ = (
        Index("idx_config_unique", "id"),
    )
