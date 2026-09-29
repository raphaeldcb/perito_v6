from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, Numeric, UniqueConstraint, LargeBinary
from app.models.types import JSONBType
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from .base import Base, TimestampMixin


class Kanban(Base, TimestampMixin):
    __tablename__ = "kanbans"

    id = Column(Integer, primary_key=True)
    perito_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    nome = Column(String(100), default="Meu Kanban")
    descricao = Column(Text)

    # Relationships
    colunas = relationship("KanbanColuna", back_populates="kanban", cascade="all, delete-orphan")
    cartoes = relationship("KanbanCartao", back_populates="kanban", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_kanbans_perito", "perito_id"),
    )


class KanbanColuna(Base, TimestampMixin):
    __tablename__ = "kanban_coluna"

    id = Column(Integer, primary_key=True)
    kanban_id = Column(Integer, ForeignKey("kanbans.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    posicao = Column(Integer, nullable=False)
    cor = Column(String(20), default="#3498db")

    # Relationships
    kanban = relationship("Kanban", back_populates="colunas")
    cartoes = relationship("KanbanCartao", back_populates="coluna")

    __table_args__ = (
        Index("idx_colunas_kanban", "kanban_id"),
    )


class KanbanCartao(Base, TimestampMixin):
    __tablename__ = "kanban_cartao"

    id = Column(Integer, primary_key=True)
    kanban_id = Column(Integer, ForeignKey("kanbans.id", ondelete="CASCADE"), nullable=False)
    coluna_id = Column(Integer, ForeignKey("kanban_coluna.id", ondelete="CASCADE"), nullable=False)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=True)

    titulo = Column(String(200), nullable=False)
    descricao = Column(Text)
    laudo_docx_path = Column(String(500))
    laudo_json = Column(JSONBType)  # Dados estruturados da análise
    status_revisao = Column(String(20))  # 'em_rascunho', 'revisor_assinou', 'coordenador_aprovou'
    protocolo_numero = Column(String(30))
    posicao = Column(Integer, default=0)
    protocolado_em = Column(DateTime, nullable=True)

    # Relationships
    kanban = relationship("Kanban", back_populates="cartoes")
    coluna = relationship("KanbanColuna", back_populates="cartoes")
    processo = relationship("Processo", back_populates="cartoes")
    historico = relationship("KanbanHistorico", back_populates="cartao", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_cartoes_kanban", "kanban_id"),
        Index("idx_cartoes_coluna", "coluna_id"),
        Index("idx_cartoes_processo", "processo_id"),
    )


class KanbanHistorico(Base, TimestampMixin):
    __tablename__ = "kanban_historico"

    id = Column(Integer, primary_key=True)
    cartao_id = Column(Integer, ForeignKey("kanban_cartao.id", ondelete="CASCADE"), nullable=False)
    coluna_anterior_id = Column(Integer, ForeignKey("kanban_coluna.id"), nullable=True)
    coluna_nova_id = Column(Integer, ForeignKey("kanban_coluna.id"), nullable=False)
    motivo = Column(Text)
    tipo_acao = Column(String(20), default="mover")  # mover, devolver, aviso, protocolo
    movido_por_id = Column(Integer)                   # id do usuário (auditoria, sem FK p/ evitar ciclo)
    movido_por_nome = Column(String(120))

    # Relationships
    cartao = relationship("KanbanCartao", back_populates="historico")
    coluna_anterior = relationship("KanbanColuna", foreign_keys=[coluna_anterior_id])
    coluna_nova = relationship("KanbanColuna", foreign_keys=[coluna_nova_id])

    __table_args__ = (
        Index("idx_historico_cartao", "cartao_id"),
    )


class Intimacao(Base, TimestampMixin):
    __tablename__ = "intimacao"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id", ondelete="CASCADE"), nullable=False)

    # Current v6 fields
    origem = Column(String(50), nullable=False)  # 'email', 'esaj', 'manual'
    tipo = Column(String(50))  # Ex: 'intimacao', 'notificacao', 'citacao'
    assunto = Column(String(200))
    conteudo = Column(Text)  # Texto extraído do PDF/email
    pdf_path = Column(String(500))  # Caminho do PDF original
    txt_path = Column(String(500))  # Caminho do TXT extraído (pypdf ou OCR)
    json_path = Column(String(500))  # Caminho do JSON análise Qwen
    md_path = Column(String(500))  # Caminho do MD formatado
    dados_estruturados = Column(JSONBType)  # Dados extraídos (partes, datas, etc)
    status = Column(String(50), default="pendente")  # pendente, processada, analisada, erro
    erros = Column(Text)  # Mensagens de erro se houver
    external_id = Column(String(100))  # ex: message-id do email, ID no Projuris
    source_system = Column(String(50), default="manual")

    # Legacy migration fields (imported from old Perito system)
    prazo = Column(DateTime, nullable=True)  # prazo_calculado do legacy
    acao_recomendada = Column(String(500), nullable=True)  # ação recomendada
    fundamentacao_legal = Column(Text, nullable=True)  # fundamentação legal
    tipo_ato = Column(String(100), nullable=True)  # tipo de ato (Despacho, etc)

    # Relationships
    processo = relationship("Processo", back_populates="intimacoes")
    oficio = relationship("Oficio", back_populates="intimacao")

    __table_args__ = (
        Index("idx_intimacao_status", "status"),
        Index("idx_intimacao_external", "source_system", "external_id"),
        Index("idx_intimacao_processo_id", "processo_id"),
        Index("idx_intimacao_tipo_ato", "tipo_ato"),
    )


class OfficioTemplateVersion(Base, TimestampMixin):
    """Template de ofício com versionamento e sincronização OneDrive."""
    __tablename__ = "oficio_template_version"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    nome = Column(String(255), nullable=False)  # "Proposta Honorários", "Defesa Valor", etc
    tipo = Column(String(50), nullable=False)  # 'proposta', 'defesa', 'pagamento_final'
    versao_numero = Column(Integer, nullable=False)  # 1, 2, 3, etc
    versao_string = Column(String(20), nullable=False)  # "v1.0", "v2.1", etc
    conteudo_docx = Column(LargeBinary, nullable=False)  # arquivo .docx binário
    placeholders = Column(JSONBType, default={})  # {"{{NUMERO_PROCESSO}}": "...", ...}

    # Sincronização OneDrive (FASE 3)
    hash_docx = Column(String(64), nullable=True)  # SHA-256 para detectar mudanças
    source = Column(String(20), default='manual', nullable=False)  # 'manual' ou 'onedrive'
    onedrive_item_id = Column(String(255), nullable=True)  # ID do arquivo no OneDrive
    last_sync_at = Column(DateTime, nullable=True)  # Quando foi sincronizado pela última vez

    created_by_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    is_ativa = Column(Boolean, default=True, nullable=False)
    descricao = Column(Text, nullable=True)
    tags = Column(JSONBType, default=[])  # ["honorários", "perícia", "2024"]

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="template_versions_criadas")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="template_versions_atualizadas")
    oficios = relationship("Oficio", back_populates="template_version")

    __table_args__ = (
        UniqueConstraint('tipo', 'versao_numero', name='uq_oficio_template_tipo_versao'),
        Index("idx_template_tipo", "tipo"),
        Index("idx_template_ativa", "is_ativa"),
        Index("idx_template_source", "source"),
        Index("idx_template_onedrive_id", "onedrive_item_id"),
    )


class Oficio(Base, TimestampMixin):
    __tablename__ = "oficio"

    id = Column(Integer, primary_key=True)
    intimacao_id = Column(Integer, ForeignKey("intimacao.id"), nullable=False)
    processo_id = Column(Integer, ForeignKey("processo.id"), nullable=False)
    cartao_id = Column(Integer, ForeignKey("kanban_cartao.id"), nullable=True)
    revisor_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    revisor_timestamp = Column(DateTime, default=None, nullable=True)
    template_version_id = Column(String(36), ForeignKey("oficio_template_version.id"), nullable=True)

    tipo = Column(String(50), default="requerimento")  # requerimento, manifestacao, outro
    tipo_origem = Column(String(20), default="modelo")  # 'modelo' ou 'upload_adhoc'
    template_upload_temp_id = Column(String(100), nullable=True)  # ref ao upload temporário
    arquivo_docx_path = Column(String(500))
    arquivo_pdf_path = Column(String(500))
    numero_protocolo = Column(String(50))  # preenchido após protocolo
    status = Column(String(50), default="gerado")  # gerado, protocolo_enfileirado, protocolado, erro, aguardando_revisao

    placeholders_mapeados = Column(JSONBType, default={})  # {"{{CAMPO}}": "valor_mapeado"}
    campos_manuais = Column(JSONBType, default=[])  # ["{{DESLOCAMENTO}}", "{{VALOR_DESLOCAMENTO}}"]
    erros = Column(Text)

    # Relationships
    intimacao = relationship("Intimacao", back_populates="oficio")
    processo = relationship("Processo", back_populates="oficios")
    cartao = relationship("KanbanCartao")
    revisor = relationship("User", foreign_keys=[revisor_id])
    template_version = relationship("OfficioTemplateVersion", back_populates="oficios")

    __table_args__ = (
        Index("idx_oficio_status", "status"),
        Index("idx_oficio_cartao", "cartao_id"),
        Index("idx_oficio_revisor", "revisor_id"),
        Index("idx_oficio_template_version", "template_version_id"),
    )
