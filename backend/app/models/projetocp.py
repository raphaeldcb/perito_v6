"""
ProjetoCP Models — Processo + auth tables (Comarca, Vara, Juiz)

PHASE 1: Core entities para gestão processual.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin
import enum


class StatusComarca(str, enum.Enum):
    ATIVO = "Ativo"
    INATIVO = "Inativo"


class Comarca(Base, TimestampMixin):
    """
    Unidade jurisdicional de primeira instância.
    Ex.: Comarca de Cuiabá, Comarca de Rondonópolis, etc.
    """
    __tablename__ = "comarca"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), unique=True, nullable=False, index=True)
    codigo_cnj = Column(String(20), unique=True, nullable=True, index=True)  # Código CNJ de vara
    uf = Column(String(2), nullable=False, index=True)  # Estado (MT, SP, RJ, etc.)
    municipio = Column(String(150), nullable=True)
    status = Column(Enum(StatusComarca), default=StatusComarca.ATIVO)

    # Relacionamentos
    varas = relationship("Vara", back_populates="comarca", cascade="all, delete-orphan")
    juizes = relationship("Juiz", back_populates="comarca", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Comarca {self.nome}/{self.uf}>"


class StatusVara(str, enum.Enum):
    ATIVO = "Ativo"
    INATIVO = "Inativo"


class Vara(Base, TimestampMixin):
    """
    Vara dentro de uma Comarca.
    Ex.: Vara Cível, Vara Criminal, Vara de Família, etc.
    """
    __tablename__ = "vara"

    id = Column(Integer, primary_key=True, index=True)
    comarca_id = Column(Integer, ForeignKey("comarca.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False, index=True)
    codigo_cnj = Column(String(20), nullable=True)  # Código CNJ de vara
    tipo = Column(String(100), nullable=True)  # Cível, Criminal, Família, Trabalho, etc.
    status = Column(Enum(StatusVara), default=StatusVara.ATIVO)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    comarca = relationship("Comarca", back_populates="varas")
    juizes = relationship("Juiz", back_populates="vara")

    def __repr__(self):
        return f"<Vara {self.nome}>"


class StatusJuiz(str, enum.Enum):
    ATIVO = "Ativo"
    APOSENTADO = "Aposentado"
    SUBSTITUIDO = "Substituído"


class Juiz(Base, TimestampMixin):
    """
    Magistrado (juiz) responsável pela decisão processual.
    """
    __tablename__ = "juiz"

    id = Column(Integer, primary_key=True, index=True)
    comarca_id = Column(Integer, ForeignKey("comarca.id"), nullable=False, index=True)
    vara_id = Column(Integer, ForeignKey("vara.id"), nullable=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    cpf = Column(String(20), nullable=True, unique=True, index=True)
    registro_cnj = Column(String(50), nullable=True, unique=True, index=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(20), nullable=True)
    status = Column(Enum(StatusJuiz), default=StatusJuiz.ATIVO)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    comarca = relationship("Comarca", back_populates="juizes")
    vara = relationship("Vara", back_populates="juizes")

    def __repr__(self):
        return f"<Juiz {self.nome}>"


class TipoPericia(str, enum.Enum):
    JUDICIAL = "Judicial"
    EXTRAJUDICIAL = "Extrajudicial"


class StatusProcesso(str, enum.Enum):
    PROTOCOLADO = "Protocolado"
    EM_ANDAMENTO = "Em Andamento"
    CONCLUIDO = "Concluído"
    CANCELADO = "Cancelado"
    ARQUIVADO = "Arquivado"
