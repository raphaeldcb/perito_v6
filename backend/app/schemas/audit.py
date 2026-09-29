"""Schemas Pydantic para audit logging."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ComunicacoesAuditLogSchema(BaseModel):
    """Audit log entry for Comunicações operations (LGPD art. 48)."""
    id: int
    user_id: Optional[int] = None
    action: str
    resource: str
    status_code: int
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    details: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogListSchema(BaseModel):
    """Paginated list of audit logs."""
    total: int
    page: int
    page_size: int
    items: list[ComunicacoesAuditLogSchema]


class AuditLogFilterSchema(BaseModel):
    """Filter parameters for audit log queries."""
    user_id: Optional[int] = None
    action: Optional[str] = None
    status_code: Optional[int] = None
    days: int = 7

    class Config:
        from_attributes = True
