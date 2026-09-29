from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.id"))
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc
    resource = Column(String(100), nullable=False)  # users, tools, roles, etc
    resource_id = Column(Integer)
    old_value = Column(Text)  # JSON string of previous state
    new_value = Column(Text)  # JSON string of new state
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    status = Column(String(20), default="success")  # success, error

    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource} by user_id={self.user_id}>"
