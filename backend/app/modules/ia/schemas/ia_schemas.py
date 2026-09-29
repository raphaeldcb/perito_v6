"""
IA module schemas (Pydantic DTOs).

Defines request/response models for analysis, RAG search, and chat endpoints.
"""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Request schemas
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request for Qwen analysis."""

    text: str = Field(..., min_length=1, max_length=50000, description="Text to analyze")
    processo_id: Optional[int] = Field(None, description="Associated process ID")
    context: Optional[dict[str, Any]] = Field(None, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Analisar os fatos desta perícia contábil...",
                "processo_id": 1,
                "context": {"tipo_pericia": "contábil", "area": "10"},
            }
        }


class RAGSearchRequest(BaseModel):
    """Request for RAG semantic search."""

    query: str = Field(..., min_length=1, max_length=5000, description="Search query")
    top_k: int = Field(5, ge=1, le=50, description="Number of results")
    area: Optional[str] = Field(None, description="Filter by expertise area")
    filters: Optional[dict[str, Any]] = Field(None, description="Additional filters")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "perícia contábil em contrato",
                "top_k": 5,
                "area": "contábil",
                "filters": {"document_type": "laudo"},
            }
        }


# ============================================================================
# Response schemas
# ============================================================================

class RAGContextSchema(BaseModel):
    """Single RAG search result."""

    id: int = Field(..., description="Document chunk ID")
    source_file: str = Field(..., description="Source file name")
    content: str = Field(..., description="Chunk text")
    area: Optional[str] = Field(None, description="Expertise area")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    tags: Optional[List[str]] = Field(None, description="Tags")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "source_file": "laudo_2024_001.pdf",
                "content": "A análise da perícia contábil evidencia...",
                "area": "contábil",
                "relevance_score": 0.87,
                "tags": ["contábil", "análise"],
            }
        }


class AnalysisResponse(BaseModel):
    """Response from Qwen analysis."""

    id: int = Field(..., description="Analysis record ID")
    analysis_result: str = Field(..., description="Qwen analysis output")
    model: str = Field(..., description="LLM model used")
    provider: str = Field(..., description="LLM provider (ollama/claude)")
    input_tokens: Optional[int] = Field(None, description="Input token count")
    output_tokens: Optional[int] = Field(None, description="Output token count")
    cost_usd: float = Field(default=0.0, description="Cost (Claude API only)")
    status: str = Field(..., description="Status: completed/error")
    error_detail: Optional[str] = Field(None, description="Error if status=error")
    rag_context: Optional[List[RAGContextSchema]] = Field(
        None, description="RAG results used as context"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "analysis_result": "A análise sugere...",
                "model": "perito-qwen",
                "provider": "ollama",
                "input_tokens": 500,
                "output_tokens": 800,
                "cost_usd": 0.0,
                "status": "completed",
                "error_detail": None,
                "rag_context": [
                    {
                        "id": 1,
                        "source_file": "laudo_2024_001.pdf",
                        "content": "...",
                        "area": "contábil",
                        "relevance_score": 0.87,
                        "tags": ["contábil"],
                    }
                ],
                "created_at": "2025-08-10T12:00:00Z",
            }
        }


class ChatRequest(BaseModel):
    """Request for stateless IA chat."""

    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    processo_id: Optional[int] = Field(None, description="Process context")
    use_rag: bool = Field(True, description="Enable RAG context search")
    context: Optional[dict[str, Any]] = Field(None, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qual é a interpretação desta cláusula?",
                "processo_id": 1,
                "use_rag": True,
                "context": {"area": "contábil"},
            }
        }


class ChatResponse(BaseModel):
    """Response from IA chat."""

    id: int = Field(..., description="Analysis record ID")
    message: str = Field(..., description="IA response")
    rag_context: Optional[List[RAGContextSchema]] = Field(
        None, description="RAG results used"
    )
    tokens_used: dict[str, int] = Field(
        ..., description="Token counts (input/output)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "message": "A cláusula estabelece...",
                "rag_context": [],
                "tokens_used": {"input": 500, "output": 800},
                "created_at": "2025-08-10T12:00:00Z",
            }
        }
