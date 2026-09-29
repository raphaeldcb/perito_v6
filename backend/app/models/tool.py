from sqlalchemy import Column, Integer, String, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin


class AccessLevel(str, enum.Enum):
    public = "public"
    user = "user"
    power_user = "power_user"
    admin = "admin"


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    url = Column(String(255), nullable=False)
    component = Column(String(100))  # React component name
    access_level = Column(SQLEnum(AccessLevel), default=AccessLevel.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(String(20), default="1.0.0")
    config = Column(Text)  # JSON string for extra config (renamed from 'metadata' which is reserved)

    permissions = relationship("ToolPermission", back_populates="tool")

    def __repr__(self):
        return f"<Tool {self.name}>"
