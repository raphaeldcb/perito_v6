"""ESAJ download tracking model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from datetime import datetime
from app.models.base import Base, TimestampMixin


class EsajDownload(Base, TimestampMixin):
    """Track ESAJ PDF downloads from /v6/data/autos/tjms/

    Maps downloaded files back to processo records for reconciliation.
    """
    __tablename__ = "esaj_download"

    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_cnj = Column(String(25), nullable=True, index=True)  # Extract from filename
    arquivo_path = Column(Text, nullable=True)  # Full path to PDF
    tamanho = Column(Integer, nullable=True)  # File size in bytes
    status = Column(String(50), nullable=False, default="downloaded", index=True)  # downloaded, failed, pending, retry
    tentativas = Column(Integer, nullable=False, default=0)  # Retry counter
    last_error = Column(Text, nullable=True)  # Error message if status=failed
    downloaded_at = Column(DateTime, nullable=True, index=True)  # Timestamp of successful download

    def __repr__(self):
        return f"<EsajDownload {self.numero_cnj} processo_id={self.processo_id} status={self.status}>"
