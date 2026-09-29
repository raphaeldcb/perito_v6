"""Model for LGPD audit logging of Comunicações operations (art. 48)."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, ForeignKey, desc
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class ComunicacoesAuditLog(Base):
    """Audit log for all Comunicações operations.

    LGPD art. 48 compliance: logs all requests to /comunicacoes/* routes
    to track data processing activities.
    """
    __tablename__ = "comunicacoes_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    action = Column(String(50), nullable=False, comment="HTTP method: GET, POST, PUT, DELETE, PATCH")
    resource = Column(String(255), nullable=False, comment="API endpoint path, e.g., /api/v1/comunicacoes/painel/statistics")
    status_code = Column(Integer, nullable=False, comment="HTTP response status code")
    client_ip = Column(String(45), nullable=True, comment="Client IPv4 or IPv6 address")
    user_agent = Column(String(500), nullable=True, comment="HTTP User-Agent header")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Request timestamp")
    details = Column(Text, nullable=True, comment="JSON with query params, response summary, errors")

    user = relationship("User", backref="comunicacoes_audit_logs")

    __table_args__ = (
        Index("idx_comunicacoes_audit_timestamp", desc(timestamp)),
        Index("idx_comunicacoes_audit_user_action", "user_id", "action"),
        Index("idx_comunicacoes_audit_resource", "resource"),
        Index("idx_comunicacoes_audit_status", "status_code"),
    )

    def __repr__(self):
        return f"<ComunicacoesAuditLog {self.action} {self.resource} by user_id={self.user_id}>"
