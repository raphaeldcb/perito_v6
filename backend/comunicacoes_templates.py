"""Models para templates de resposta automática de comunicações judiciais."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.sql import func
import enum

from app.database import Base


class TipoRespostaEnum(str, enum.Enum):
    """Tipos de resposta automática."""
    ACUSACAO_RECEBIMENTO = "acusacao_recebimento"  # Confirmar recebimento
    INTIMACAO = "intimacao"  # Responder a intimação
    MANDADO = "mandado"  # Responder a mandado
    SENTENCA = "sentenca"  # Reconhecer sentença
    AGRAVO = "agravo"  # Responder a agravo
    RECURSO = "recurso"  # Responder a recurso
    OUTROS = "outros"  # Outro tipo


class ComunicacaoTemplate(Base):
    """Template de resposta automática para comunicações judiciais."""

    __tablename__ = "comunicacao_template"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)  # "Intimação - Resposta Padrão"
    tipo = Column(Enum(TipoRespostaEnum), nullable=False)  # Tipo de resposta
    descricao = Column(Text, nullable=True)  # "Usar para intimações de audiência"

    # Conteúdo do email
    assunto_template = Column(String(500), nullable=False)  # "Re: {assunto_original}"
    corpo_html = Column(Text, nullable=False)  # Template HTML com placeholders
    corpo_texto = Column(Text, nullable=False)  # Versão plain-text

    # Placeholders suportados em templates:
    # {remetente} — nome/email de quem enviou
    # {assunto_original} — assunto do email original
    # {data_recebimento} — data que o email foi recebido
    # {numero_processo} — número do processo (se extraído)
    # {vara} — vara judicial
    # {comarca} — comarca
    # {empresa} — nome da empresa/IPC
    # {endereço} — endereço da empresa

    # Configuração de ativação
    ativo = Column(Boolean, default=True)
    aplicar_automaticamente = Column(Boolean, default=False)  # Enviar sem aprovação manual?

    # Triggers (quando aplicar este template)
    triggar_palavras_chave = Column(String(500), nullable=True)  # "intimação,audiência" (CSV)
    triggar_tipo_processo = Column(String(100), nullable=True)  # "judicial" ou "extrajudicial"
    triggar_min_confianca = Column(Integer, default=80)  # Confiança mínima (0-100)

    # Metadata
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())
    atualizado_por = Column(String(255), nullable=True)  # Email do usuário que criou/editou

    class Config:
        from_attributes = True


class ComunicacaoResposta(Base):
    """Registro de resposta automática enviada."""

    __tablename__ = "comunicacao_resposta"

    id = Column(Integer, primary_key=True, index=True)
    mensagem_id = Column(Integer, nullable=False)  # FK para ComunicacaoMensagem.id
    template_id = Column(Integer, nullable=False)  # FK para ComunicacaoTemplate.id

    # Email enviado
    destinatario = Column(String(255), nullable=False)  # Email para responder
    assunto_enviado = Column(String(500), nullable=False)
    corpo_html_enviado = Column(Text, nullable=False)  # Conteúdo renderizado

    # Status
    status = Column(String(50), default="PENDENTE")  # PENDENTE / ENVIADA / ERRO / LIDA
    erro_mensagem = Column(Text, nullable=True)  # Se falhou: por quê?

    # Metadata
    aprovado_por = Column(String(255), nullable=True)  # Quem aprovou envio manual (se aplicável)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    lido_em = Column(DateTime(timezone=True), nullable=True)  # Quando remetente original leu?
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Tracking
    message_id = Column(String(255), nullable=True)  # Message-ID para vincular resposta recebida

    class Config:
        from_attributes = True
