from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ToolPermission(Base, TimestampMixin):
    __tablename__ = "tool_permissions"

    id = Column(Integer, primary_key=True, index=True)
    tool_id = Column(Integer, ForeignKey("tools.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    can_access = Column(Boolean, default=True, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)

    tool = relationship("Tool", back_populates="permissions")

    def __repr__(self):
        return f"<ToolPermission tool_id={self.tool_id} role_id={self.role_id}>"
