from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Boolean, Text
from datetime import datetime
from app.models.base import Base, TimestampMixin
import enum

class TipoParentescoDNA(str, enum.Enum):
    CRI = "CRI"  # Criança/Investigante
    MA1 = "MA1"  # Mãe
    MA2 = "MA2"  # Mãe dos SMIs
    SP1 = "SP1"  # Suposto Pai
    SP2 = "SP2"
    SP3 = "SP3"
    SMI1 = "SMI1"  # Suposto Meio-Irmão (com MA2)
    SMI2 = "SMI2"
    SMI3 = "SMI3"
    ST1 = "ST1"  # Suposto Tio Paterno
    ST2 = "ST2"
    ST3 = "ST3"
    AGM = "AGM"  # Suposto Avó Materna
    AGF = "AGF"  # Suposto Avô Paterno
    OUTRO = "OUTRO"

class ResultadoDNA(str, enum.Enum):
    EXCLUSAO = "EXCLUSÃO"
    INCLUSAO = "INCLUSÃO"

class ParticipanteDNA(Base, TimestampMixin):
    __tablename__ = "participante_dna"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(Enum(TipoParentescoDNA), nullable=False)  # CRI, MA1, MA2, SP1-3, SMI1-3, ST1-3, AGM, AGF, OUTRO
    nome = Column(String(255), nullable=False)
    requerente = Column(Boolean, default=False)  # Quem está pedindo
    requerido = Column(Boolean, default=False)  # Quem está sendo testado

    def __repr__(self):
        return f"<ParticipanteDNA {self.tipo} - {self.nome}>"

class EnquadramentoDNA(Base, TimestampMixin):
    __tablename__ = "enquadramento_dna"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String(20), nullable=False)  # PD0101, RD0301, etc
    descricao = Column(Text, nullable=False)  # Mãe, criança e suposto pai
    valor_particular = Column(Float)  # R$ 800,00
    valor_judicial = Column(Float)  # R$ 600,00
    resultado = Column(Enum(ResultadoDNA), nullable=False)  # EXCLUSÃO ou INCLUSÃO
    probabilidade = Column(Float, nullable=True)  # 99.9% se INCLUSÃO
    observacoes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<EnquadramentoDNA {self.codigo}>"
