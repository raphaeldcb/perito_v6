"""Mixins — shared model behaviors."""
from datetime import datetime
from sqlalchemy import Column, DateTime


class TimestampMixin:
    """Adds created_at and updated_at columns."""
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
