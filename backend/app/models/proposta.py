"""Motor de Propostas — Geração inteligente de propostas de honorários.

Fluxo: PDF intimação → OCR + análise Qwen → propostas similares → valor recomendado
       → geração DOCX → Kanban de revisão → aprovação Master → Protocolo A3
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Text, DateTime, ForeignKey, Index, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.types import JSONBType
from app.models.base import Base, TimestampMixin


class PropostaStatus(str, enum.Enum):
    """Estados do workflow de propostas."""
    EXTRAINDO = "extraindo"           # OCR em andamento
    CLASSIFICANDO = "classificando"   # Analisando área
    ANALISANDO = "analisando"         # Qwen gerando recomendação
    DRAFT = "draft"                   # Proposta gerada, aguardando revisão
    ANALISTA_REVISAO = "analista_revisao"      # Analista da área revisando
    COORD_REVISAO = "coord_revisao"            # Coordenador revisando
    MASTER_REVISAO = "master_revisao"          # Master revisando
    APROVADO = "aprovado"             # Pronto para protocolar
    PROTOCOLADO = "protocolado"       # Enviado A3
    VENCIDO = "vencido"               # Prazo passou
    RECUSADO = "recusado"             # Master recusou


class PropostaMotor(Base, TimestampMixin):
    """Análise e geração de proposta de honorários."""
    __tablename__ = "proposta_motor"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False)
    intimacao_id = Column(Integer, ForeignKey("intimacao.id"), nullable=True)
    cartao_id = Column(Integer, ForeignKey("kanban_cartao.id"), nullable=True)

    # OCR Extract
    pdf_path = Column(String(500))                      # PDF original
    txt_extraido = Column(Text)                         # Texto bruto do OCR
    json_extraido = Column(JSONBType, default={})       # JSON estruturado

    # Dados estruturados do PDF
    juiz = Column(String(200))
    comarca = Column(String(120))
    tribunal = Column(String(50))                       # TJMT, TJSP, etc
    pedido = Column(String(100))                        # proposta_honorarios, defesa_valor
    prazo_dias = Column(Integer)
    data_vencimento = Column(DateTime)
    fls = Column(Integer)                               # número de folhas
    valor_causa = Column(Numeric(15, 2))
    partes = Column(JSONBType, default=[])              # ["AUTOR", "RÉU"]
    materia = Column(String(200))                       # "Imissão de Posse"

    # Classificação
    area_id = Column(Integer)                           # 10=Contábil, 30=Eng, 40=Grafo, etc
    area_nome = Column(String(100))
    area_confianca = Column(Numeric(3, 2))              # 0.0-1.0

    # Análise Qwen
    propostas_similares = Column(JSONBType, default=[]) # Top 5 comparativas
    valor_recomendado = Column(Numeric(15, 2))
    valor_alternativa = Column(Numeric(15, 2))         # caso conservador
    motivo_recomendacao = Column(Text)                 # "Juiz frequente aprova teto CNJ"
    analise_juiz = Column(Text)                        # Histórico e frequência
    analise_complexidade = Column(Text)                # Fatores de ajuste

    # Documento gerado
    arquivo_docx_path = Column(String(500))
    arquivo_docx_hash = Column(String(64))             # SHA-256 para revisão

    # Workflow
    status = Column(String(30), default="extraindo", index=True)
    analista_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    coord_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    master_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    # Aprovações
    valor_aprovado = Column(Numeric(15, 2))            # Valor final após aprovações
    analista_aprovado_em = Column(DateTime)
    coord_aprovado_em = Column(DateTime)
    master_aprovado_em = Column(DateTime)
    master_motivo_rejeicao = Column(Text)              # Se recusado

    # Integração com ofício
    oficio_id = Column(Integer, ForeignKey("oficio.id"), nullable=True)

    # Audit
    erros = Column(Text)
    logs = Column(JSONBType, default=[])

    # Relationships
    processo = relationship("Processo", foreign_keys=[processo_id])
    intimacao = relationship("Intimacao", foreign_keys=[intimacao_id])
    cartao = relationship("KanbanCartao", foreign_keys=[cartao_id])
    analista = relationship("User", foreign_keys=[analista_id], backref="propostas_analisadas")
    coordenador = relationship("User", foreign_keys=[coord_id], backref="propostas_coordenadas")
    master = relationship("User", foreign_keys=[master_id], backref="propostas_masterizadas")
    oficio = relationship("Oficio", foreign_keys=[oficio_id])
    feedback_items = relationship("PropostaFeedback", back_populates="proposta", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_proposta_status", "status"),
        Index("idx_proposta_processo", "processo_id"),
        Index("idx_proposta_intimacao", "intimacao_id"),
        Index("idx_proposta_area", "area_id"),
        Index("idx_proposta_data_venc", "data_vencimento"),
        Index("idx_proposta_cartao", "cartao_id"),
    )


class PropostaFeedback(Base, TimestampMixin):
    """Aprendizado do master: valor proposto vs aprovado, motivo edição."""
    __tablename__ = "proposta_feedback"

    id = Column(Integer, primary_key=True)
    proposta_id = Column(Integer, ForeignKey("proposta_motor.id", ondelete="CASCADE"), nullable=False)
    juiz = Column(String(200))
    comarca = Column(String(120))
    area_id = Column(Integer)

    valor_proposto = Column(Numeric(15, 2))
    valor_aprovado = Column(Numeric(15, 2))
    diferenca_pct = Column(Numeric(5, 2))              # (aprovado - proposto) / proposto * 100

    motivo = Column(String(100))  # "Complexidade acima padrão", "Juiz exigente", etc
    motivo_texto_livre = Column(Text)
    master_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    master_nome = Column(String(120))

    # Aprendizagem
    complexidade_ajustada = Column(Boolean, default=False)  # mudou fator de ajuste?
    novo_teto_juiz = Column(Numeric(15, 2))                 # redefiniu teto deste juiz?

    # Relationships
    proposta = relationship("PropostaMotor", back_populates="feedback_items")

    __table_args__ = (
        Index("idx_feedback_proposta", "proposta_id"),
        Index("idx_feedback_juiz_area", "juiz", "area_id"),
    )


class PropostaAnalisador(Base, TimestampMixin):
    """Cache/histórico de análises Qwen para otimizar (não refazer se mesmo PDF hash)."""
    __tablename__ = "proposta_analisador_cache"

    id = Column(Integer, primary_key=True)
    pdf_hash = Column(String(64), unique=True, index=True)  # SHA-256 do PDF
    json_extraido = Column(JSONBType)
    area_id = Column(Integer)
    area_nome = Column(String(100))
    area_confianca = Column(Numeric(3, 2))

    analise_json = Column(JSONBType)  # Resultado completo da análise Qwen
    valor_recomendado = Column(Numeric(15, 2))
    motivo = Column(Text)

    processado_em = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_analisador_pdf_hash", "pdf_hash"),
    )
