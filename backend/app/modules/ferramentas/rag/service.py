# v6/backend/app/modules/ferramentas/{tool}/service.py
"""RAG Service — Business logic for vector search indexing and queries."""
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.services import rag_indexer
from .schemas import Chunk, IndexarInput, BuscarInput

logger = logging.getLogger(__name__)


def indexar_chunks(db: Session, payload: IndexarInput) -> dict:
    """Indexa chunks de embedding já pronto (uso: mac_agent).

    Substitui os chunks de (origem, ref_id) pelos novos já embeddados.
    """
    rag_indexer.ensure_schema(db)

    if not payload.chunks:
        raise ValueError("sem chunks")

    # Delete old chunks for this (origem, ref_id)
    db.execute(
        text("DELETE FROM documento_rag WHERE origem=:o AND ref_id IS NOT DISTINCT FROM :r"),
        {"o": payload.origem, "r": payload.ref_id}
    )

    # Insert new chunks
    for c in payload.chunks:
        try:
            vec = rag_indexer.vec_literal(c.embedding)
        except ValueError as e:
            raise ValueError(str(e))
        db.execute(text("""
            INSERT INTO documento_rag (origem, ref_id, chunk_idx, texto, embedding)
            VALUES (:o, :r, :i, :t, (:e)::vector)
        """), {
            "o": payload.origem,
            "r": payload.ref_id,
            "i": c.chunk_idx,
            "t": c.texto,
            "e": vec
        })

    db.commit()
    logger.info(f"RAG indexou {len(payload.chunks)} chunks de {payload.origem}/{payload.ref_id}")

    return {
        "indexados": len(payload.chunks),
        "origem": payload.origem,
        "ref_id": payload.ref_id
    }


def buscar_por_embedding(db: Session, payload: BuscarInput) -> dict:
    """Fallback — retorna chunks sem pgvector."""
    rag_indexer.ensure_schema(db)
    
    k = max(1, min(payload.k, 50))
    filtro = "WHERE origem = :origem" if payload.origem else ""
    params = {"k": k}
    if payload.origem:
        params["origem"] = payload.origem
    
    rows = db.execute(text(f"""
        SELECT origem, ref_id, chunk_idx, texto, 0.5 AS similaridade
        FROM documento_rag {filtro}
        ORDER BY LENGTH(texto) DESC LIMIT :k
    """), params).mappings().all()
    
    return {"resultados": [dict(r) for r in rows]}


def search_semantico(db: Session, q: str, tipo: str | None, k: int) -> dict:
    """Busca semântica server-side: embedda `q` via Ollama e retorna top-k.

    Usada para fundamentar prompts do Qwen (laudo, ofício, etc) com
    contexto histórico real do acervo (processos, intimações, laudos, financeiro).
    """
    if tipo and tipo not in rag_indexer.ORIGENS_VALIDAS:
        raise ValueError(f"tipo inválido. Use um de: {sorted(rag_indexer.ORIGENS_VALIDAS)}")

    try:
        resultados = rag_indexer.search(db, q, tipo=tipo, k=k)
    except RuntimeError as e:
        # Ollama indisponível — relança como 503 (indisponibilidade temporária)
        raise RuntimeError(str(e))

    return {"query": q, "tipo": tipo, "resultados": resultados}


def get_stats(db: Session) -> dict:
    """Retorna estatísticas do índice RAG."""
    return rag_indexer.stats(db)
