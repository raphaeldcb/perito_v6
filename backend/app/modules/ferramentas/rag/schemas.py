"""RAG Schemas — Pydantic models for vector search API."""
from pydantic import BaseModel


class Chunk(BaseModel):
    """Um pedaço de texto já embeddado (do mac_agent ou similar)."""
    chunk_idx: int = 0
    texto: str
    embedding: list[float]


class IndexarInput(BaseModel):
    """Payload para POST /rag/indexar — substitui chunks de (origem, ref_id)."""
    origem: str
    ref_id: str | None = None
    chunks: list[Chunk]


class BuscarInput(BaseModel):
    """Payload para POST /rag/buscar — busca por embedding já pronto."""
    embedding: list[float] | None = None
    k: int = 5
    origem: str | None = None  # filtra por tipo, se quiser só laudos p.ex.
