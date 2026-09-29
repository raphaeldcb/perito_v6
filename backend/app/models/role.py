from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # admin, power_user, user, public
    description = Column(Text)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"
