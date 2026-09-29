"""Cérebro 3.0 — Intelligence Engine models.

Tables:
- AprendizadoEvento: Every learning event (action in the system)
- PadrãoRAG: Learned patterns with confidence scoring
- AuditoriaCAP: Audit trail for access control
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from app.models.types import JSONBType, ArrayType
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.mixins import TimestampMixin


class AprendizadoEvento(Base, TimestampMixin):
    """Every action that feeds the Knowledge Hub."""
    __tablename__ = 'aprendizado_evento'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    client_id = Column(Integer, nullable=True)  # Client context (future: FK to cliente table)

    tipo = Column(String(50), nullable=False)  # job_concluido, intimacao_recebida, laudo_gerado, etc
    contexto = Column(JSONBType, nullable=False)  # {processo_id, laudo_id, area, tribunal, ...}
    origem = Column(String(50), nullable=False)  # 'esaj', 'meta', 'job_queue', 'financeiro', 'marketing'

    padrão_id = Column(Integer, ForeignKey('padrão_rag.id', ondelete='SET NULL'), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    usuario = relationship('User', foreign_keys=[usuario_id])
    padrão = relationship('PadrãoRAG', foreign_keys=[padrão_id])

    def __repr__(self):
        return f"<AprendizadoEvento({self.tipo}, usuario={self.usuario_id}, score={getattr(self.padrão, 'score', 'N/A')})>"


class PadrãoRAG(Base, TimestampMixin):
    """Learned patterns from historical data."""
    __tablename__ = 'padrão_rag'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    owner_id = Column(Integer, nullable=True)  # Who learned it (for attribution)

    dominio = Column(String(50), nullable=False)  # engenharia, vendas, financeiro, operacional, inteligência
    tipo = Column(String(100), nullable=False)  # tipo_laudo_grafotecnica, prazo_média_esaj, audiência_meta_25_30, etc
    descricao = Column(Text, nullable=False)

    frequency = Column(Integer, nullable=False, default=1)  # How many times observed
    aceitos = Column(Integer, nullable=False, default=0)  # How many user accepted
    score = Column(Float, nullable=False, default=0.5)  # Confidence (0.0 - 0.99)

    embedding = Column(ArrayType(Float), nullable=True)  # Vector for RAG similarity search
    meta_info = Column(JSONBType, nullable=True)  # {exemplos: [id1, id2, ...], tags: ['urgente', ...]}

    is_public = Column(Boolean, nullable=False, default=False)  # Share with other users?

    usuario = relationship('User', foreign_keys=[usuario_id])
    eventos = relationship('AprendizadoEvento', back_populates='padrão')

    @property
    def confidence_rate(self) -> float:
        """Acceptance rate (0-1)."""
        if self.frequency == 0:
            return 0.0
        return min(1.0, self.aceitos / self.frequency)

    @property
    def is_high_confidence(self) -> bool:
        """Pattern is trustworthy (score >= 0.7)."""
        return self.score >= 0.7

    def recalc_score(self):
        """Recalculate score based on frequency + acceptance + bootstrap penalty.

        Formula: score = (0.6 * freq_norm + 0.4 * acceptance_rate) * bootstrap_factor

        Bootstrap: patterns with < 5 examples max out at 0.5 (avoid overfitting).
        """
        if self.frequency == 0:
            self.score = 0.0
            return

        freq_normalized = min(1.0, self.frequency / 100)  # Normalize to 0-1
        acceptance_rate = self.confidence_rate

        # Bootstrap penalty: < 5 examples → score caps at 0.5
        bootstrap_factor = min(1.0, self.frequency / 5) if self.frequency < 5 else 1.0

        self.score = min(0.99, (0.6 * freq_normalized + 0.4 * acceptance_rate) * bootstrap_factor)

    def __repr__(self):
        return f"<PadrãoRAG({self.tipo}, score={self.score:.2f}, freq={self.frequency})>"


class AuditoriaCAP(Base, TimestampMixin):
    """Audit log for Cérebro Access Policy."""
    __tablename__ = 'auditoria_cerebro'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)

    endpoint = Column(String(100), nullable=False)  # /cerebro/graph, /cerebro/recommend, etc
    operacao = Column(String(20), nullable=False)  # GET, POST, DELETE

    recursos_acessados = Column(JSONBType, nullable=True)  # {usuario_ids: [1,2,...], dominio: 'vendas', pattern_ids: [5,6,...]}
    resultado = Column(String(20), nullable=False)  # sucesso, erro, negado
    motivo_negacao = Column(String(255), nullable=True)  # "usuário 5 não tem acesso a padrão 42"

    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    usuario = relationship('User', foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<AuditoriaCAP({self.endpoint} {self.operacao} → {self.resultado}, user={self.usuario_id})>"
