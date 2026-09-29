"""Cérebro Cofre — Secure Vault com Multi-device Approval.

Tables:
- SecretVault: Credenciais criptografadas (Azure Key Vault backed)
- SecretRequest: Pedido de acesso
- SecretApproval: Aprovação multi-device
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from app.models.types import JSONBType
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.mixins import TimestampMixin
import enum


class SecretType(str, enum.Enum):
    """Tipos de secret."""
    DATABASE_PASSWORD = "database_password"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    OAUTH_TOKEN = "oauth_token"
    SSH_KEY = "ssh_key"
    WEBHOOK_SECRET = "webhook_secret"
    OTHER = "other"


class SecretVault(Base, TimestampMixin):
    """Credencial segura (armazenada em Azure Key Vault)."""
    __tablename__ = 'secret_vault'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)

    nome = Column(String(100), nullable=False, unique=True)  # 'db-prod', 'api-meta', etc
    tipo = Column(Enum(SecretType), nullable=False)
    descricao = Column(Text, nullable=True)

    # Azure Key Vault reference (não armazenamos valor aqui!)
    azure_key_vault_id = Column(String(255), nullable=False)  # URN no AKV

    meta_info = Column(JSONBType, nullable=True)  # {rotacao_dias: 90, critico: true, ...}

    # Access control
    pode_acessar = Column(JSONBType, nullable=True)  # {usuario_ids: [1,2,3], roles: ['admin']}
    requer_aprovacao = Column(Boolean, nullable=False, default=True)
    tempo_expiracao_horas = Column(Integer, nullable=False, default=1)  # Token expira em 1h

    # Tracking
    ultimo_acesso = Column(DateTime, nullable=True)
    ultimo_acessado_por = Column(Integer, ForeignKey('usuario.id', ondelete='SET NULL'), nullable=True)
    ultimo_acessado_de_ip = Column(String(50), nullable=True)

    usuario = relationship('User', foreign_keys=[usuario_id])
    requisicoes = relationship('SecretRequest', back_populates='secret')
    acessos_log = relationship('SecretAccessLog', back_populates='secret')

    def __repr__(self):
        return f"<SecretVault({self.nome}, tipo={self.tipo.value})>"


class SecretRequest(Base, TimestampMixin):
    """Pedido de acesso a um secret."""
    __tablename__ = 'secret_request'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    secret_id = Column(Integer, ForeignKey('secret_vault.id', ondelete='CASCADE'), nullable=False)

    motivo = Column(Text, nullable=True)  # Por que precisa da credencial
    ip_request = Column(String(50), nullable=False)  # De onde pediu
    user_agent = Column(String(255), nullable=True)

    # Status
    status = Column(String(20), nullable=False, default='pendente')  # pendente, aprovado, rejeitado, expirado
    token = Column(String(255), nullable=True)  # Token temporário (UUID)
    token_expira_em = Column(DateTime, nullable=True)

    # Timestamps
    pedido_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=False)  # Auto-expira em 5 min se não aprovado

    usuario = relationship('User', foreign_keys=[usuario_id])
    secret = relationship('SecretVault', back_populates='requisicoes')
    aprovacoes = relationship('SecretApproval', back_populates='request')

    def __repr__(self):
        return f"<SecretRequest(usuario={self.usuario_id}, secret={self.secret_id}, status={self.status})>"

    @property
    def esta_expirado(self) -> bool:
        """Request expirou (>5 min sem aprovação)."""
        return datetime.utcnow() > self.expira_em


class SecretApproval(Base, TimestampMixin):
    """Aprovação de acesso (multi-device)."""
    __tablename__ = 'secret_approval'

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('secret_request.id', ondelete='CASCADE'), nullable=False)
    aprovador_id = Column(Integer, ForeignKey('usuario.id', ondelete='SET NULL'), nullable=True)

    aprovado = Column(Boolean, nullable=False)  # True = aprovado, False = rejeitado
    motivo_rejeicao = Column(Text, nullable=True)

    ip_approval = Column(String(50), nullable=False)  # De onde aprovou
    user_agent = Column(String(255), nullable=True)  # Mobile, desktop, etc

    aprovado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship('SecretRequest', back_populates='aprovacoes')
    aprovador = relationship('User', foreign_keys=[aprovador_id])

    def __repr__(self):
        return f"<SecretApproval(request={self.request_id}, aprovado={self.aprovado})>"


class SecretAccessLog(Base, TimestampMixin):
    """Audit log de cada acesso a secret."""
    __tablename__ = 'secret_access_log'

    id = Column(Integer, primary_key=True)
    secret_id = Column(Integer, ForeignKey('secret_vault.id', ondelete='CASCADE'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)

    acao = Column(String(20), nullable=False)  # 'acessado', 'deletado', 'rotacionado'
    motivo = Column(Text, nullable=True)
    resultado = Column(String(20), nullable=False)  # 'sucesso', 'erro', 'negado'
    erro_msg = Column(Text, nullable=True)

    ip_address = Column(String(50), nullable=False)
    user_agent = Column(String(255), nullable=True)

    acessado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    secret = relationship('SecretVault', back_populates='acessos_log')
    usuario = relationship('User', foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<SecretAccessLog(secret={self.secret_id}, acao={self.acao}, resultado={self.resultado})>"
