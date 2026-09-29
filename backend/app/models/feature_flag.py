from sqlalchemy import Column, Integer, String, Boolean, Text
from .base import Base, TimestampMixin


class FeatureFlag(Base, TimestampMixin):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True)
    nome = Column(String(50), unique=True, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    descricao = Column(Text, nullable=True)
