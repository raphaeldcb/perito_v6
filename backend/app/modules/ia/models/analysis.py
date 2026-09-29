"""
IA module models — Analysis and RAG result tracking.

Analysis model stores Qwen analysis results for audit/caching.
RAGResult model stores semantically-searched document chunks.
"""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin


class Analysis(Base, TimestampMixin):
    """Stores Qwen LLM analysis results for processes/documents."""

    __tablename__ = "ia_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    processo_id = Column(Integer, nullable=True)  # FK deferred to Phase 3

    # Input
    input_text = Column(Text, nullable=False)  # Raw text sent to Qwen
    input_tokens = Column(Integer)  # Token count from API

    # Output
    analysis_result = Column(Text, nullable=False)  # Qwen response
    output_tokens = Column(Integer)  # Token count from API

    # Metadata
    model = Column(String(50), default="perito-qwen")  # Which LLM was used
    provider = Column(String(20), default="ollama")  # ollama or claude
    cost_usd = Column(Float, default=0.0)  # Cost tracking (Claude API only)

    # Status
    status = Column(String(20), default="completed")  # pending, completed, error
    error_detail = Column(Text)  # If status=error

    # Context
    rag_context = Column(JSON)  # Embedded RAG search results used

    # Indexing
    is_indexed = Column(Integer, default=False)  # Whether used for RAG corpus

    # Relationships deferred to Phase 3 (Wave 1 integration)
    # user = relationship("User", back_populates="ia_analyses")
    # processo = relationship("Processo", back_populates="ia_analyses")

    def __repr__(self):
        return f"<Analysis id={self.id} user={self.user_id} status={self.status}>"


class RAGDocument(Base, TimestampMixin):
    """
    Stores document chunks for RAG search.
    Typically populated from acervo de laudos on OneDrive.
    """

    __tablename__ = "ia_rag_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Document metadata
    source_file = Column(String(255), nullable=False)  # e.g., "laudo_2024_001.pdf"
    source_url = Column(String(500))  # OneDrive URL or local path
    document_type = Column(String(50), default="laudo")  # laudo, jurisprudencia, etc

    # Content
    chunk_index = Column(Integer, default=0)  # Chunk number in document
    content = Column(Text, nullable=False)  # The actual text chunk

    # Metadata
    title = Column(String(255))  # Document title/name
    area = Column(String(50))  # Expertise area (contábil, DNA, etc)
    tags = Column(JSON)  # Tags for filtering (list of strings)

    # Embedding
    embedding = Column(JSON)  # Vector embedding (stored as JSON for now; pgvector later)
    embedding_model = Column(String(50), default="nomic-embed-text")
    is_embedded = Column(Integer, default=False)

    # Indexing
    is_indexed = Column(Integer, default=False)  # Ready for search
    relevance_score = Column(Float)  # Used during RAG search

    def __repr__(self):
        return f"<RAGDocument id={self.id} source={self.source_file} chunk={self.chunk_index}>"
