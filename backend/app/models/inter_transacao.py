"""Modelo para rastreamento de transações com Banco Inter."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SQLEnum
import enum

from app.models.base import Base


class StatusTransacao(str, enum.Enum):
    """Status de uma transação no Banco Inter."""
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    PROCESSANDO = "processando"
    FALHOU = "falhou"
    CANCELADO = "cancelado"


class TipoOperacao(str, enum.Enum):
    """Tipo de operação bancária."""
    PIX = "pix"
    CNAB = "cnab"
    BOLETO = "boleto"
    TRANSFERENCIA = "transferencia"


class InterTransacao(Base):
    """
    Rastreamento de transações com Banco Inter.

    Serve para:
    - Reconciliação (linked a Coletador ou Processo)
    - Auditoria (quem iniciou, quando, quanto, status)
    - Webhook (quando Banco Inter confirma, atualizar este registro)
    - Retry (se falhou, tentar novamente)
    """
    __tablename__ = "inter_transacao"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificadores
    id_unico = Column(String(36), unique=True, nullable=False)  # UUID para idempotência
    transaction_id = Column(String(50), nullable=True, unique=True)  # Do Banco Inter

    # Operação
    tipo_operacao = Column(SQLEnum(TipoOperacao), nullable=False)
    descricao = Column(String(100), nullable=False)

    # Valores
    valor_centavos = Column(Integer, nullable=False)  # 100000 = R$ 1.000,00
    valor_real = Column(Float, nullable=True)  # Cache: valor em R$

    # Detalhes
    chave_destino = Column(String(100), nullable=True)  # PIX: CPF, email, telefone
    agencia_destino = Column(String(10), nullable=True)  # TED/DOC: agência banco destino
    conta_destino = Column(String(20), nullable=True)  # TED/DOC: conta

    # Status
    status = Column(SQLEnum(StatusTransacao), default=StatusTransacao.PENDENTE)
    status_detalhe = Column(Text, nullable=True)  # Mensagem de erro se falhou

    # Rastreamento
    iniciado_por_user_id = Column(Integer, nullable=True)  # FK User
    process_id = Column(Integer, nullable=True)  # FK Processo (se pagamento perifo)
    coletador_id = Column(Integer, nullable=True)  # FK Coletador (se pagamento coletador)

    # Datas
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmado_em = Column(DateTime, nullable=True)  # Quando Banco Inter confirmou
    tentativas = Column(Integer, default=0)
    proxima_tentativa = Column(DateTime, nullable=True)

    # Resposta do Banco Inter (raw JSON)
    resposta_banco = Column(Text, nullable=True)  # JSON stringified

    def __repr__(self):
        return f"<InterTransacao id={self.id} type={self.tipo_operacao} status={self.status} valor=R${self.valor_real or '?'}>"
