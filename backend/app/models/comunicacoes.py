# v6/backend/app/models/comunicacoes.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import Base


class JudicialStatus(str, enum.Enum):
    NOVO = "novo"
    PROCESSANDO = "processando"
    COMPLETO = "completo"
    PENDENTE = "pendente"
    REVISAR = "revisar"
    RASCUNHO = "rascunho"
    RESPONDIDO = "respondido"
    IGNORADO = "ignorado"
    ERRO = "erro"


class EmailMessage(Base):
    """Armazena e-mails monitorados do Microsoft Graph."""
    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True)
    # Identificadores Microsoft
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    internet_message_id = Column(String(255), unique=True, nullable=True, index=True)
    conversation_id = Column(String(255), nullable=True, index=True)

    # Remetente
    from_address = Column(String(255), nullable=False)
    from_name = Column(String(255), nullable=True)
    to_addresses = Column(Text, nullable=False)  # JSON array
    cc_addresses = Column(Text, nullable=True)   # JSON array

    # Conteúdo
    subject = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    received_datetime = Column(DateTime, nullable=False)

    # Classificação judicial
    is_judicial = Column(Boolean, default=False, index=True)
    judicial_confidence = Column(Float, nullable=True)  # 0.0-1.0
    judicial_reason = Column(Text, nullable=True)

    # Extração de dados processuais
    tribunal = Column(String(255), nullable=True)
    vara = Column(String(255), nullable=True)
    comarca = Column(String(255), nullable=True)
    numero_processo = Column(String(20), nullable=True, index=True)
    pedido = Column(Text, nullable=True)
    prazo = Column(String(100), nullable=True)

    # Status
    status = Column(String(50), default=JudicialStatus.NOVO.value, index=True)

    # Resposta
    resposta_sugerida = Column(Text, nullable=True)
    resposta_editada = Column(Text, nullable=True)
    resposta_enviada = Column(DateTime, nullable=True)

    # Anexos
    has_attachments = Column(Boolean, default=False)
    attachments_data = Column(Text, nullable=True)  # JSON

    # Marcadores
    analyzed_at = Column(DateTime, nullable=True)  # Quando foi analisado pelo Perito v6
    categories = Column(Text, nullable=True)  # JSON array com categorias do Outlook

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailMessage {self.message_id} from {self.from_address}>"


class EmailConfig(Base):
    """Configurações do módulo de monitoramento."""
    __tablename__ = "email_config"

    id = Column(Integer, primary_key=True)

    # Conta monitorada
    mailbox_email = Column(String(255), unique=True, nullable=False)

    # Intervalo (em minutos)
    intervalo_minutos = Column(Integer, default=5, nullable=False)

    # Status
    ativo = Column(Boolean, default=True)
    ultima_execucao = Column(DateTime, nullable=True)
    proxima_execucao = Column(DateTime, nullable=True)

    # Campos obrigatórios (JSON)
    campos_obrigatorios = Column(Text, default='{"tribunal": true, "vara": true, "numero_processo": true, "pedido": true}')

    # Modo resposta
    modo_resposta = Column(String(50), default="rascunho")  # "rascunho" ou "automatico"

    # Template padrão
    template_id = Column(Integer, ForeignKey("email_template.id"), nullable=True)
    template = relationship("EmailTemplate")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailTemplate(Base):
    """Templates de resposta configuráveis."""
    __tablename__ = "email_template"

    id = Column(Integer, primary_key=True)

    nome = Column(String(255), nullable=False)
    assunto = Column(String(500), nullable=False)
    corpo = Column(Text, nullable=False)

    # Variáveis suportadas: {{tribunal}}, {{vara}}, {{numero_processo}}, {{pedido}}, {{campos_faltantes}}, {{assinatura}}
    ativo = Column(Boolean, default=True)
    padrao = Column(Boolean, default=False)  # Um por vez

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailTemplate {self.nome}>"


class EmailFeedback(Base):
    """Aprendizado com alterações do usuário."""
    __tablename__ = "email_feedback"

    id = Column(Integer, primary_key=True)

    email_message_id = Column(Integer, ForeignKey("email_messages.id"), nullable=False)

    # O que foi sugerido vs o que foi corrigido
    resposta_original = Column(Text, nullable=True)
    resposta_corrigida = Column(Text, nullable=True)

    # Campos corrigidos
    tribunal_original = Column(String(255), nullable=True)
    tribunal_corrigido = Column(String(255), nullable=True)

    vara_original = Column(String(255), nullable=True)
    vara_corrigida = Column(String(255), nullable=True)

    comarca_original = Column(String(255), nullable=True)
    comarca_corrigida = Column(String(255), nullable=True)

    numero_processo_original = Column(String(20), nullable=True)
    numero_processo_corrigido = Column(String(20), nullable=True)

    pedido_original = Column(Text, nullable=True)
    pedido_corrigido = Column(Text, nullable=True)

    usuario_id = Column(Integer, nullable=True)  # Se houver multi-user

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmailFeedback email_id={self.email_message_id}>"
