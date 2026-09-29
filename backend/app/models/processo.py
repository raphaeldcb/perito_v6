from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, JSON, Numeric, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin
import enum

class TipoPericia(str, enum.Enum):
    JUDICIAL = "Judicial"
    EXTRAJUDICIAL = "Extrajudicial"
    AT = "AT"

class StatusProcesso(str, enum.Enum):
    # All values match legacy database format exactly
    ATIVO = "ativo"
    PROTOCOLADO = "protocolado"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    ARQUIVADO = "Arquivado"
    CONCLUIDO = "Concluído"
    CANCELADO = "Cancelado"

class Processo(Base, TimestampMixin):
    __tablename__ = "processo"

    id = Column(Integer, primary_key=True)
    numero_cnj = Column(String(25), unique=True, nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"))
    external_id = Column(String(100))
    source_system = Column(String(50))

    # Processo info
    titulo = Column(String(200))
    descricao = Column(Text)
    autor = Column(String(200))
    reu = Column(String(200))
    especialidade = Column(String(100))
    doc = Column(String(30))
    tipo = Column(String(30))  # Legacy field
    responsavel = Column(String(120))
    data_nomeacao = Column(DateTime)

    # Judicial info
    vara = Column(String(100))
    tribunal = Column(String(100))
    juiz = Column(String(200))
    comarca = Column(String(100), index=True)

    # Perícia
    tipo_pericia = Column(String(50), index=True, default="Judicial")
    setor = Column(String(50), index=True)
    status = Column(String(50), default="protocolado")
    prioridade = Column(String(20), default="Média")

    # Financeiro
    honorarios = Column(Numeric(12, 2))
    forma_recebimento = Column(String(20))
    pago = Column(Boolean)
    data_aceite = Column(DateTime)
    data_pagamento = Column(DateTime)
    prazo = Column(DateTime)

    # Partes & Perícia
    partes = Column(JSON, default=list)  # [{papel, nome, doc}, ...]
    participantes_dna = Column(JSON, default=list)  # [{tipo, nome_real, nome_doc}, ...]
    laboratorio = Column(String(150))

    # Financeiro
    deslocamento = Column(JSON)

    # Documentos
    documentos = Column(JSON, default=list)

    responsavel_id = Column(Integer, ForeignKey("usuario.id"))

    # Relationships
    cartoes = relationship("KanbanCartao", back_populates="processo")
    intimacoes = relationship("Intimacao", back_populates="processo")
    oficios = relationship("Oficio", back_populates="processo")

    def __repr__(self):
        return f"<Processo {self.numero_cnj}>"
