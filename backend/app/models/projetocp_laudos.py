"""
ProjetoCP Phase 2: Extended Laudo Models + Quesitos + Area/Financeiro Integration
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, JSON, Numeric, Enum, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin
import enum


class AreaPericia(str, enum.Enum):
    """Áreas de perícia segundo tabela de honorários"""
    GRAFOTECNICA = "grafotecnica"  # 40
    ENGENHARIA_CIVIL = "engenharia_civil"  # 01
    ENGENHARIA_MECANICA = "engenharia_mecanica"  # 02
    ENGENHARIA_ELETRICA = "engenharia_eletrica"  # 03
    AGRONOMIA = "agronomia"  # 04
    MEDICINA = "medicina"  # 05
    ODONTOLOGIA = "odontologia"  # 06
    PSICOLOGIA = "psicologia"  # 07
    CONTABILIDADE = "contabilidade"  # 08
    ECONOMIA = "economia"  # 09
    TOPOGRAFIA = "topografia"  # 10
    DESLOCAMENTO = "deslocamento"  # Adicional


class LaudoStatus(str, enum.Enum):
    """Status de evolução do laudo"""
    RASCUNHO = "rascunho"
    ESTRUTURADO = "estruturado"  # Quesitos extraídos
    CONTEUDO_INICIAL = "conteudo_inicial"  # Respaldo principal pronto
    RESPALDO_COMPLETO = "respaldo_completo"  # Toda revisão + anexos
    REVISAO_INTERNA = "revisao_interna"
    REVISAO_CLIENTE = "revisao_cliente"
    PRONTO_PROTOCOLO = "pronto_protocolo"
    PROTOCOLADO = "protocolado"
    FINALIZADO = "finalizado"


class LaudoQuesito(Base, TimestampMixin):
    """Quesitos extraídos da intimação/contrato por Qwen"""
    __tablename__ = "laudo_quesito"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    numero = Column(Integer, nullable=False)  # Seq: 1,2,3...
    pergunta = Column(Text, nullable=False)  # "Qual a causa do dano?"
    resposta = Column(Text, nullable=True)  # Resposta estruturada (pode vir do RAG)
    tipo = Column(String(50), default="ordinario")  # ordinario, prejudicial, mitigatorio
    relevancia = Column(Integer, default=5)  # 1-10 score
    fontes_rag = Column(JSON, nullable=True)  # [{"id":123, "distancia":0.85, "texto":"..."}]
    status = Column(String(30), default="nao_respondido")  # respondido, revisado, finalizado

    laudo = relationship("Laudo")

    __table_args__ = (
        Index("idx_laudo_quesito_laudo", "laudo_id"),
        Index("idx_laudo_quesito_numero", "laudo_id", "numero"),
    )


class LaudoAnexo(Base, TimestampMixin):
    """Anexos e documentação suporte do laudo"""
    __tablename__ = "laudo_anexo"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)  # foto, desenho, tabela, parecer_tecnico, etc
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    arquivo_path = Column(String(500), nullable=False)
    pagina_referencia = Column(Integer, nullable=True)  # Em qual página do laudo
    tamanho_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    upload_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    laudo = relationship("Laudo")

    __table_args__ = (
        Index("idx_laudo_anexo_laudo", "laudo_id"),
    )


class LaudoHonorario(Base, TimestampMixin):
    """Cálculo de honorários por laudo (integração com módulo financeiro)"""
    __tablename__ = "laudo_honorario"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False, unique=True)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False)
    area = Column(String(50), nullable=False)  # grafotecnica, engenharia_civil, etc
    tipo_calculo = Column(String(30), default="tabela")  # tabela, consenso, combinado
    valor_base = Column(Numeric(12, 2), nullable=False)  # valor tabela OAB / consensual
    adicional_complexidade = Column(Numeric(12, 2), default=0)  # % ou valor fixo
    adicional_deslocamento = Column(Numeric(12, 2), default=0)  # km * valor/km
    deducao_desconto = Column(Numeric(12, 2), default=0)  # negociação
    valor_final = Column(Numeric(12, 2), nullable=False)  # (base + adic) - deducao
    percentual_sucumbencia = Column(Numeric(5, 2), nullable=True)  # % se vencer (90% típico)
    data_calculo = Column(DateTime, default=datetime.utcnow)
    calculado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    laudo = relationship("Laudo")

    __table_args__ = (
        Index("idx_laudo_honorario_laudo", "laudo_id"),
        Index("idx_laudo_honorario_processo", "processo_id"),
    )


class LaudoRevenda(Base, TimestampMixin):
    """Rastreabilidade de criação de laudo (modelo Qwen, versões, editores)"""
    __tablename__ = "laudo_revenda"

    id = Column(Integer, primary_key=True)
    laudo_id = Column(Integer, ForeignKey("laudo.id", ondelete="CASCADE"), nullable=False)
    versao_numero = Column(Integer, default=1)
    etapa = Column(String(50), nullable=False)  # extracao_quesitos, geracao_conteudo, revisao, etc
    modelo_ia = Column(String(50), default="qwen-3.6")  # qual IA gerou
    tempo_processamento_segundos = Column(Integer, nullable=True)
    prompt_usado = Column(Text, nullable=True)  # para debug/auditoria
    resultado_raw = Column(JSON, nullable=True)  # Resposta bruta antes processamento
    status = Column(String(30), default="em_processamento")
    erro = Column(Text, nullable=True)
    processado_por = Column(String(50), default="mac_agent")  # mac_agent, windows_agent, api_direct

    laudo = relationship("Laudo")

    __table_args__ = (
        Index("idx_laudo_revenda_laudo", "laudo_id"),
    )


class LaudoEspecialidadeStats(Base, TimestampMixin):
    """Rastreamento de performance de geração por especialidade (retroalimentação)"""
    __tablename__ = "laudo_especialidade_stats"

    id = Column(Integer, primary_key=True)
    especialidade = Column(String(50), unique=True, nullable=False)
    total_gerados = Column(Integer, default=0)  # Total de laudos gerados
    total_acertos_100 = Column(Integer, default=0)  # Aprovados sem alterações
    taxa_sucesso_percentual = Column(Numeric(5, 2), default=0)  # %
    confianca_proxima_geracao = Column(Integer, default=40)  # 40-95%, sobe com sucessos
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_especialidade_stats_espec", "especialidade"),
    )


# Estender relacionamento na model Laudo já existente (será patchado no main init)
# Adicionar em app/models/__init__.py:
# laudo.Laudo.quesitos = relationship("LaudoQuesito", back_populates="laudo", cascade="all, delete-orphan")
# laudo.Laudo.anexos = relationship("LaudoAnexo", back_populates="laudo", cascade="all, delete-orphan")
# laudo.Laudo.honorario = relationship("LaudoHonorario", back_populates="laudo", cascade="all, delete-orphan")
# laudo.Laudo.revenda_log = relationship("LaudoRevenda", back_populates="laudo", cascade="all, delete-orphan")
