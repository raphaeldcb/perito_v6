"""
IA module — Qwen analysis engine + RAG semantic search.

Wave 1 Modularization: Public interface (schemas + router only).
Internal implementation (models, repositories, services) isolated.

Provides:
- Schemas: AnalysisRequest, AnalysisResponse, RAGSearchRequest, ChatRequest, ChatResponse
- Router: IA-01 to IA-05 endpoints (analyze, search, chat, history, get)

Never import models, repositories, or services from this module directly.
All inter-module communication via app.shared DTOs and exceptions.

Note: Services (QwenService, RAGService) should be obtained via
dependency injection (FastAPI Depends), not imported directly.
"""

from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    RAGSearchRequest,
    RAGContextSchema,
    ChatRequest,
    ChatResponse,
)
from .routes import router

__all__ = [
    # Schemas (PUBLIC — inter-module communication contracts)
    "AnalysisRequest",
    "AnalysisResponse",
    "RAGSearchRequest",
    "RAGContextSchema",
    "ChatRequest",
    "ChatResponse",
    # Routes (PUBLIC — FastAPI integration)
    "router",
]
