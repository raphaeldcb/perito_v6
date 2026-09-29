from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Index, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class MidiaOrigem(Base, TimestampMixin):
    __tablename__ = "midia_origem"

    id = Column(Integer, primary_key=True)
    nome = Column(String(50), unique=True, nullable=False)
    descricao = Column(Text, nullable=True)

    laudos = relationship("LaudoForense", back_populates="origem_midia")


class ClienteForense(Base, TimestampMixin):
    __tablename__ = "clientes_forense"

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    cnpj_cpf = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    telefone = Column(String(20), nullable=True)

    laudos = relationship("LaudoForense", back_populates="cliente")

    __table_args__ = (
        Index("idx_cliente_forense_cnpj_cpf", "cnpj_cpf"),
        Index("idx_cliente_forense_email", "email"),
    )


class StatusPagamento(str, Enum):
    PENDENTE = "pendente"
    COMPLETADO = "completado"
    REEMBOLSADO = "reembolsado"


class LaudoForense(Base, TimestampMixin):
    __tablename__ = "laudos_forense"

    id = Column(Integer, primary_key=True)
    numero_laudo = Column(String(30), unique=True, nullable=False)
    arquivo_hash = Column(String(64), nullable=False)
    arquivo_nome_original = Column(String(500), nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes_forense.id"), nullable=True)
    origem_midia_id = Column(Integer, ForeignKey("midia_origem.id"), nullable=False)
    descricao_contextual = Column(Text, nullable=True)

    # Resultados de análise
    veredicto = Column(String(50), nullable=True)  # "Autêntico", "Falso", "Inconclusivo"
    authenticity_score = Column(Float, nullable=True)  # 0.0 - 1.0
    consensus_apis = Column(JSON, nullable=True)  # Resultado do consenso das APIs

    # Análises detalhadas
    analise_espectral = Column(JSON, nullable=True)  # FFT, Wavelet, DCT
    analise_biometrica = Column(JSON, nullable=True)  # Landmarks, blink rate, rPPG
    analise_gemini = Column(JSON, nullable=True)  # Resultado estruturado Gemini

    # Pagamento
    status_pagamento = Column(String(20), default=StatusPagamento.PENDENTE.value)
    stripe_payment_intent_id = Column(String(255), nullable=True)

    # Arquivos gerados
    pdf_path = Column(String(500), nullable=True)
    docx_path = Column(String(500), nullable=True)

    # Relacionamentos
    cliente = relationship("ClienteForense", back_populates="laudos")
    origem_midia = relationship("MidiaOrigem", back_populates="laudos")

    __table_args__ = (
        Index("idx_laudo_forense_numero", "numero_laudo"),
        Index("idx_laudo_forense_cliente", "cliente_id"),
        Index("idx_laudo_forense_status", "status_pagamento"),
        Index("idx_laudo_forense_hash", "arquivo_hash"),
    )


class ForensicAnalysis(Base, TimestampMixin):
    __tablename__ = "forensic_analysis"

    id = Column(Integer, primary_key=True)

    # Analysis results data (JSON or structured)
    arquivo_hash_md5 = Column(String(32), nullable=True, comment="Hash MD5 do arquivo analisado")
    arquivo_nome = Column(String(255), nullable=True, comment="Nome original do arquivo")
    arquivo_tipo = Column(String(50), nullable=True, comment="Tipo MIME do arquivo")
    arquivo_tamanho_bytes = Column(Integer, nullable=True, comment="Tamanho em bytes")
    resultado_json = Column(JSON, nullable=True, comment="Resultado completo da análise em JSON")

    # Verdict and confidence
    veredicto_final = Column(String(50), nullable=True, comment="Veredicto final (Autêntico/Falso/Inconclusivo)")
    confianca_consenso = Column(Float, nullable=True, comment="Score de confiança (0.0-1.0)")
    nivel_risco = Column(String(50), nullable=True, comment="Nível de risco identificado")

    # Signature and tracking
    assinado = Column(Boolean, default=False, nullable=False, comment="Indica se foi assinado digitalmente")
    assinado_por = Column(String(255), nullable=True, comment="CPF/email de quem assinou")
    timestamp_assinatura = Column(DateTime, nullable=True, comment="Data/hora da assinatura")
    certificado_a3_serial = Column(String(255), nullable=True, comment="Número serial do certificado A3 usado")

    # FK to related data
    processo_id = Column(Integer, nullable=True, comment="ID do processo relacionado")
    laudo_id = Column(Integer, nullable=True, comment="ID do laudo relacionado")

    # Laudo generation URLs (TASK 1 — 3 NEW COLUMNS)
    laudo_docx_url = Column(String(500), nullable=True, comment="URL do laudo DOCX no OneDrive")
    laudo_pdf_url = Column(String(500), nullable=True, comment="URL do laudo PDF no OneDrive")
    laudo_generated_at = Column(DateTime, nullable=True, comment="Timestamp de geração do laudo")

    # Timestamps
    timestamp_criacao = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Data/hora de criação")
    timestamp_conclusao = Column(DateTime, nullable=True, comment="Data/hora de conclusão da análise")
    tempo_total_ms = Column(Integer, nullable=True, comment="Tempo total de análise em milissegundos")

    __table_args__ = (
        Index("idx_forensic_analysis_hash", "arquivo_hash_md5"),
        Index("idx_forensic_analysis_processo", "processo_id"),
        Index("idx_forensic_analysis_laudo", "laudo_id"),
        Index("idx_forensic_analysis_criacao", "timestamp_criacao"),
    )
