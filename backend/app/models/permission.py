from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    action = Column(String(50), nullable=False)  # read, write, delete, admin
    resource = Column(String(50), nullable=False)  # users, tools, logs, etc
    description = Column(Text)

    role = relationship("Role", back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.role_id}:{self.action}:{self.resource}>"
